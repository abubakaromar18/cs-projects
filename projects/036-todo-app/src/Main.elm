port module Main exposing (Model, Msg(..), init, main, update, view)

{-| The Elm Architecture wiring: Model, Msg, update, view, plus two ports for
persisting to localStorage.

Data flow is one-directional:

    user event -> Msg -> update -> new Model -> view -> Html
                                 \-> Cmd (save to localStorage)

-}

import Browser
import Browser.Dom as Dom
import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (..)
import Html.Keyed as Keyed
import Json.Decode as Decode
import Json.Encode as Encode
import Task
import Todo exposing (Filter(..), Todo, TodoList)



-- PORTS


{-| Outgoing: JavaScript writes this value to localStorage.
-}
port save : Encode.Value -> Cmd msg



-- MODEL


type alias Model =
    { todos : TodoList
    , draft : String
    , filter : Filter
    , editing : Maybe { id : Int, text : String }
    }


{-| Flags are whatever JSON the host page found in localStorage (or null).
A corrupt blob simply falls back to an empty list.
-}
init : Decode.Value -> ( Model, Cmd Msg )
init flags =
    ( { todos =
            Decode.decodeValue Todo.decoder flags
                |> Result.withDefault Todo.empty
      , draft = ""
      , filter = All
      , editing = Nothing
      }
    , Cmd.none
    )



-- UPDATE


type Msg
    = UpdateDraft String
    | Add
    | Toggle Int
    | Delete Int
    | ToggleAll
    | ClearCompleted
    | SetFilter Filter
    | StartEdit Todo
    | UpdateEdit String
    | CommitEdit
    | CancelEdit
    | NoOp


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        UpdateDraft text ->
            ( { model | draft = text }, Cmd.none )

        Add ->
            persist { model | todos = Todo.add model.draft model.todos, draft = "" }

        Toggle id ->
            persist { model | todos = Todo.toggle id model.todos }

        Delete id ->
            persist { model | todos = Todo.remove id model.todos }

        ToggleAll ->
            persist { model | todos = Todo.toggleAll model.todos }

        ClearCompleted ->
            persist { model | todos = Todo.clearCompleted model.todos }

        SetFilter filter ->
            ( { model | filter = filter }, Cmd.none )

        StartEdit todo ->
            ( { model | editing = Just { id = todo.id, text = todo.title } }
            , Task.attempt (\_ -> NoOp) (Dom.focus (editInputId todo.id))
            )

        UpdateEdit text ->
            ( { model | editing = Maybe.map (\e -> { e | text = text }) model.editing }
            , Cmd.none
            )

        CommitEdit ->
            case model.editing of
                Just e ->
                    persist { model | todos = Todo.edit e.id e.text model.todos, editing = Nothing }

                Nothing ->
                    ( model, Cmd.none )

        CancelEdit ->
            ( { model | editing = Nothing }, Cmd.none )

        NoOp ->
            ( model, Cmd.none )


{-| Every change to the todo list itself is mirrored to localStorage.
-}
persist : Model -> ( Model, Cmd Msg )
persist model =
    ( model, save (Todo.encode model.todos) )



-- VIEW


view : Model -> Html Msg
view model =
    div [ class "app" ]
        [ header []
            [ h1 [] [ text "todos" ]
            , Html.form [ onSubmit Add ]
                [ input
                    [ class "new-todo"
                    , placeholder "What needs to be done?"
                    , autofocus True
                    , value model.draft
                    , onInput UpdateDraft
                    , attribute "aria-label" "New todo"
                    ]
                    []
                ]
            ]
        , viewList model
        , viewFooter model
        ]


viewList : Model -> Html Msg
viewList model =
    let
        all =
            Todo.items model.todos
    in
    if List.isEmpty all then
        p [ class "empty" ] [ text "Nothing to do yet." ]

    else
        section [ class "main" ]
            [ input
                [ class "toggle-all"
                , id "toggle-all"
                , type_ "checkbox"
                , checked (List.all .completed all)
                , onClick ToggleAll
                ]
                []
            , label [ for "toggle-all" ] [ text "Mark all as complete" ]

            -- Keyed nodes let the virtual DOM track items by id, so
            -- deleting one doesn't re-render (and re-focus) its neighbours.
            , Keyed.ul [ class "todo-list" ]
                (List.map (\t -> ( String.fromInt t.id, viewTodo model.editing t ))
                    (Todo.visible model.filter model.todos)
                )
            ]


viewTodo : Maybe { id : Int, text : String } -> Todo -> Html Msg
viewTodo editing todo =
    case editing of
        Just e ->
            if e.id == todo.id then
                li [ class "editing" ]
                    [ input
                        [ class "edit"
                        , id (editInputId todo.id)
                        , value e.text
                        , onInput UpdateEdit
                        , onBlur CommitEdit
                        , onKey [ ( "Enter", CommitEdit ), ( "Escape", CancelEdit ) ]
                        ]
                        []
                    ]

            else
                viewItem todo

        Nothing ->
            viewItem todo


viewItem : Todo -> Html Msg
viewItem todo =
    li [ classList [ ( "completed", todo.completed ) ] ]
        [ input
            [ class "toggle"
            , type_ "checkbox"
            , checked todo.completed
            , onClick (Toggle todo.id)
            , attribute "aria-label" ("Toggle " ++ todo.title)
            ]
            []
        , label [ onDoubleClick (StartEdit todo) ] [ text todo.title ]
        , button
            [ class "destroy"
            , onClick (Delete todo.id)
            , attribute "aria-label" ("Delete " ++ todo.title)
            ]
            [ text "×" ]
        ]


viewFooter : Model -> Html Msg
viewFooter model =
    let
        left =
            Todo.remaining model.todos

        total =
            List.length (Todo.items model.todos)
    in
    if total == 0 then
        text ""

    else
        footer [ class "footer" ]
            [ span [ class "count" ]
                [ strong [] [ text (String.fromInt left) ]
                , text (pluralize left " item left" " items left")
                ]
            , ul [ class "filters" ] (List.map (viewFilter model.filter) [ All, Active, Completed ])
            , if total > left then
                button [ class "clear-completed", onClick ClearCompleted ] [ text "Clear completed" ]

              else
                text ""
            ]


viewFilter : Filter -> Filter -> Html Msg
viewFilter current filter =
    let
        name =
            Todo.filterToString filter
    in
    li []
        [ button
            [ classList [ ( "selected", current == filter ) ]
            , onClick (SetFilter filter)
            ]
            [ text (String.toUpper (String.left 1 name) ++ String.dropLeft 1 name) ]
        ]



-- HELPERS


editInputId : Int -> String
editInputId id =
    "edit-" ++ String.fromInt id


pluralize : Int -> String -> String -> String
pluralize n singular plural =
    if n == 1 then
        singular

    else
        plural


{-| Fire a message for specific keys only; other keys are ignored by failing
the decoder, so no Msg is produced at all.
-}
onKey : List ( String, Msg ) -> Attribute Msg
onKey table =
    on "keydown"
        (Decode.field "key" Decode.string
            |> Decode.andThen
                (\key ->
                    case List.filter (\( k, _ ) -> k == key) table of
                        ( _, msg ) :: _ ->
                            Decode.succeed msg

                        [] ->
                            Decode.fail "ignored key"
                )
        )



-- MAIN


main : Program Decode.Value Model Msg
main =
    Browser.element
        { init = init
        , update = update
        , view = view
        , subscriptions = \_ -> Sub.none
        }
