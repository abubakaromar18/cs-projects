module TodoTests exposing (suite)

import Expect
import Fuzz
import Json.Decode as Decode
import Json.Encode as Encode
import Test exposing (Test, describe, fuzz, test)
import Todo exposing (Filter(..))


titles : Todo.TodoList -> List String
titles =
    Todo.items >> List.map .title


sample : Todo.TodoList
sample =
    Todo.empty
        |> Todo.add "buy milk"
        |> Todo.add "write tests"
        |> Todo.add "ship it"
        |> Todo.toggle 2


suite : Test
suite =
    describe "Todo"
        [ describe "add"
            [ test "appends trimmed titles in order" <|
                \_ ->
                    Todo.empty
                        |> Todo.add "  a  "
                        |> Todo.add "b"
                        |> titles
                        |> Expect.equal [ "a", "b" ]
            , test "ignores blank input" <|
                \_ ->
                    Todo.empty
                        |> Todo.add "   "
                        |> Todo.items
                        |> Expect.equal []
            , test "never reuses ids after a delete" <|
                \_ ->
                    Todo.empty
                        |> Todo.add "a"
                        |> Todo.add "b"
                        |> Todo.remove 2
                        |> Todo.add "c"
                        |> Todo.items
                        |> List.map .id
                        |> Expect.equal [ 1, 3 ]
            , fuzz (Fuzz.list Fuzz.string) "ids are always unique" <|
                \inputs ->
                    let
                        ids =
                            List.foldl Todo.add Todo.empty inputs |> Todo.items |> List.map .id
                    in
                    List.length ids
                        |> Expect.equal (List.length (dedupe ids))
            ]
        , describe "toggle / remaining"
            [ test "toggle flips one item" <|
                \_ ->
                    sample
                        |> Todo.items
                        |> List.map .completed
                        |> Expect.equal [ False, True, False ]
            , test "remaining counts active items" <|
                \_ -> Todo.remaining sample |> Expect.equal 2
            , test "toggling twice is identity" <|
                \_ -> sample |> Todo.toggle 1 |> Todo.toggle 1 |> Expect.equal sample
            ]
        , describe "toggleAll"
            [ test "completes everything when some are active" <|
                \_ -> sample |> Todo.toggleAll |> Todo.remaining |> Expect.equal 0
            , test "reactivates everything when all are complete" <|
                \_ ->
                    sample
                        |> Todo.toggleAll
                        |> Todo.toggleAll
                        |> Todo.remaining
                        |> Expect.equal 3
            ]
        , describe "edit"
            [ test "renames a todo" <|
                \_ ->
                    sample
                        |> Todo.edit 1 " buy oat milk "
                        |> titles
                        |> Expect.equal [ "buy oat milk", "write tests", "ship it" ]
            , test "editing to blank deletes" <|
                \_ -> sample |> Todo.edit 3 "  " |> titles |> Expect.equal [ "buy milk", "write tests" ]
            ]
        , describe "filters"
            [ test "Active" <|
                \_ -> Todo.visible Active sample |> List.map .title |> Expect.equal [ "buy milk", "ship it" ]
            , test "Completed" <|
                \_ -> Todo.visible Completed sample |> List.map .title |> Expect.equal [ "write tests" ]
            , test "All" <|
                \_ -> Todo.visible All sample |> List.length |> Expect.equal 3
            , test "clearCompleted drops done items" <|
                \_ -> sample |> Todo.clearCompleted |> titles |> Expect.equal [ "buy milk", "ship it" ]
            , test "string round-trip" <|
                \_ ->
                    [ All, Active, Completed ]
                        |> List.map (Todo.filterToString >> Todo.filterFromString)
                        |> Expect.equal [ All, Active, Completed ]
            ]
        , describe "JSON"
            [ test "encode/decode round-trips" <|
                \_ ->
                    Todo.encode sample
                        |> Decode.decodeValue Todo.decoder
                        |> Expect.equal (Ok sample)
            , test "decoder repairs a stale nextId" <|
                \_ ->
                    Encode.object
                        [ ( "nextId", Encode.int 1 )
                        , ( "todos"
                          , Encode.list identity
                                [ Encode.object
                                    [ ( "id", Encode.int 7 )
                                    , ( "title", Encode.string "old" )
                                    , ( "completed", Encode.bool False )
                                    ]
                                ]
                          )
                        ]
                        |> Decode.decodeValue Todo.decoder
                        |> Result.map (Todo.add "new" >> Todo.items >> List.map .id)
                        |> Expect.equal (Ok [ 7, 8 ])
            , test "rejects malformed data" <|
                \_ ->
                    Encode.string "nope"
                        |> Decode.decodeValue Todo.decoder
                        |> Result.toMaybe
                        |> Expect.equal Nothing
            ]
        ]


dedupe : List comparable -> List comparable
dedupe =
    List.foldr
        (\x acc ->
            if List.member x acc then
                acc

            else
                x :: acc
        )
        []
