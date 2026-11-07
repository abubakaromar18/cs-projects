module MainTests exposing (suite)

{-| Tests of the TEA layer: drive `update` with messages and inspect the
rendered `view` with Test.Html — no browser needed.
-}

import Expect
import Json.Encode as Encode
import Main exposing (Msg(..))
import Test exposing (Test, describe, test)
import Test.Html.Event as Event
import Test.Html.Query as Query
import Test.Html.Selector exposing (class, tag, text)
import Todo exposing (Filter(..))


start : Main.Model
start =
    Main.init Encode.null |> Tuple.first


run : List Msg -> Main.Model
run =
    List.foldl (\msg model -> Main.update msg model |> Tuple.first) start


withThree : Main.Model
withThree =
    run
        [ UpdateDraft "one"
        , Add
        , UpdateDraft "two"
        , Add
        , UpdateDraft "three"
        , Add
        , Toggle 2
        ]


suite : Test
suite =
    describe "Main"
        [ test "Add clears the draft" <|
            \_ -> withThree.draft |> Expect.equal ""
        , test "empty state message" <|
            \_ ->
                Main.view start
                    |> Query.fromHtml
                    |> Query.has [ text "Nothing to do yet." ]
        , test "renders one li per todo" <|
            \_ ->
                Main.view withThree
                    |> Query.fromHtml
                    |> Query.findAll [ class "todo-list", tag "li" ]
                    |> Query.count (Expect.equal 3)
        , test "footer shows remaining count" <|
            \_ ->
                Main.view withThree
                    |> Query.fromHtml
                    |> Query.find [ class "count" ]
                    |> Query.has [ text "2", text " items left" ]
        , test "Active filter hides completed items" <|
            \_ ->
                Main.view { withThree | filter = Active }
                    |> Query.fromHtml
                    |> Query.findAll [ tag "li", class "completed" ]
                    |> Query.count (Expect.equal 0)
        , test "clicking Clear completed sends ClearCompleted" <|
            \_ ->
                Main.view withThree
                    |> Query.fromHtml
                    |> Query.find [ class "clear-completed" ]
                    |> Event.simulate Event.click
                    |> Event.expect ClearCompleted
        , test "editing commits new title" <|
            \_ ->
                let
                    first =
                        Todo.items withThree.todos |> List.head
                in
                case first of
                    Just t ->
                        List.foldl (\m model -> Main.update m model |> Tuple.first)
                            withThree
                            [ StartEdit t, UpdateEdit "uno", CommitEdit ]
                            |> .todos
                            |> Todo.items
                            |> List.map .title
                            |> Expect.equal [ "uno", "two", "three" ]

                    Nothing ->
                        Expect.fail "expected a todo"
        , test "CancelEdit leaves the title alone" <|
            \_ ->
                case Todo.items withThree.todos of
                    t :: _ ->
                        List.foldl (\m model -> Main.update m model |> Tuple.first)
                            withThree
                            [ StartEdit t, UpdateEdit "zzz", CancelEdit ]
                            |> .todos
                            |> Expect.equal withThree.todos

                    [] ->
                        Expect.fail "expected a todo"
        ]
