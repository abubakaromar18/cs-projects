module Todo exposing
    ( Filter(..)
    , Todo
    , TodoList
    , add
    , clearCompleted
    , decoder
    , edit
    , empty
    , encode
    , filterFromString
    , filterToString
    , items
    , remaining
    , remove
    , toggle
    , toggleAll
    , visible
    )

{-| Pure domain logic for the todo list.

Nothing in this module knows about HTML or effects: every function is a
plain transformation `TodoList -> TodoList`. That keeps the business rules
trivially testable and lets `Main` stay a thin layer of The Elm Architecture.

`TodoList` is an opaque type: callers can only build and change it through
the functions below, so invariants (unique ids, trimmed non-empty titles)
cannot be broken from outside.

-}

import Json.Decode as Decode exposing (Decoder)
import Json.Encode as Encode


type alias Todo =
    { id : Int
    , title : String
    , completed : Bool
    }


{-| Opaque wrapper. `nextId` is a monotonically increasing counter so ids are
never reused, even after deletions.
-}
type TodoList
    = TodoList { nextId : Int, todos : List Todo }


type Filter
    = All
    | Active
    | Completed



-- CONSTRUCTION


empty : TodoList
empty =
    TodoList { nextId = 1, todos = [] }


items : TodoList -> List Todo
items (TodoList list) =
    list.todos



-- UPDATES


{-| Append a todo. Blank titles (after trimming) are ignored.
-}
add : String -> TodoList -> TodoList
add rawTitle (TodoList list) =
    let
        title =
            String.trim rawTitle
    in
    if String.isEmpty title then
        TodoList list

    else
        TodoList
            { nextId = list.nextId + 1
            , todos = list.todos ++ [ { id = list.nextId, title = title, completed = False } ]
            }


toggle : Int -> TodoList -> TodoList
toggle id =
    updateWhere id (\t -> { t | completed = not t.completed })


{-| Rename a todo. Editing a title down to nothing deletes it, which is the
classic TodoMVC behaviour.
-}
edit : Int -> String -> TodoList -> TodoList
edit id rawTitle list =
    let
        title =
            String.trim rawTitle
    in
    if String.isEmpty title then
        remove id list

    else
        updateWhere id (\t -> { t | title = title }) list


remove : Int -> TodoList -> TodoList
remove id =
    mapTodos (List.filter (\t -> t.id /= id))


{-| Mark everything done, or, if everything is already done, mark everything
active again.
-}
toggleAll : TodoList -> TodoList
toggleAll list =
    let
        target =
            not (List.all .completed (items list))
    in
    mapTodos (List.map (\t -> { t | completed = target })) list


clearCompleted : TodoList -> TodoList
clearCompleted =
    mapTodos (List.filter (not << .completed))



-- QUERIES


remaining : TodoList -> Int
remaining list =
    List.length (List.filter (not << .completed) (items list))


visible : Filter -> TodoList -> List Todo
visible filter list =
    case filter of
        All ->
            items list

        Active ->
            List.filter (not << .completed) (items list)

        Completed ->
            List.filter .completed (items list)


filterToString : Filter -> String
filterToString filter =
    case filter of
        All ->
            "all"

        Active ->
            "active"

        Completed ->
            "completed"


filterFromString : String -> Filter
filterFromString s =
    case s of
        "active" ->
            Active

        "completed" ->
            Completed

        _ ->
            All



-- JSON (used for localStorage persistence via ports)


encode : TodoList -> Encode.Value
encode (TodoList list) =
    Encode.object
        [ ( "nextId", Encode.int list.nextId )
        , ( "todos", Encode.list encodeTodo list.todos )
        ]


encodeTodo : Todo -> Encode.Value
encodeTodo t =
    Encode.object
        [ ( "id", Encode.int t.id )
        , ( "title", Encode.string t.title )
        , ( "completed", Encode.bool t.completed )
        ]


{-| Decodes a stored list. `nextId` is recomputed defensively so that a
hand-edited or stale blob can never cause id collisions.
-}
decoder : Decoder TodoList
decoder =
    Decode.map2
        (\storedNext todos ->
            let
                maxId =
                    List.maximum (List.map .id todos) |> Maybe.withDefault 0
            in
            TodoList { nextId = max storedNext (maxId + 1), todos = todos }
        )
        (Decode.oneOf [ Decode.field "nextId" Decode.int, Decode.succeed 1 ])
        (Decode.field "todos" (Decode.list todoDecoder))


todoDecoder : Decoder Todo
todoDecoder =
    Decode.map3 Todo
        (Decode.field "id" Decode.int)
        (Decode.field "title" Decode.string)
        (Decode.field "completed" Decode.bool)



-- HELPERS


mapTodos : (List Todo -> List Todo) -> TodoList -> TodoList
mapTodos f (TodoList list) =
    TodoList { list | todos = f list.todos }


updateWhere : Int -> (Todo -> Todo) -> TodoList -> TodoList
updateWhere id f =
    mapTodos
        (List.map
            (\t ->
                if t.id == id then
                    f t

                else
                    t
            )
        )
