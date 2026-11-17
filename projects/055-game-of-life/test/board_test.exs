defmodule GameOfLife.BoardTest do
  use ExUnit.Case, async: true
  doctest GameOfLife

  alias GameOfLife.{Board, Cell, Grid, Patterns}

  defp start_board(grid) do
    {:ok, board} = Board.start_link(grid)
    on_exit(fn -> if Process.alive?(board), do: Board.stop(board) end)
    board
  end

  test "spawns one process per cell" do
    board = start_board(Grid.new(7, 5))
    assert Board.process_count(board) == 35
  end

  test "blinker oscillates on the process board" do
    {:ok, g} = GameOfLife.centered("blinker", 5, 5)
    board = start_board(g)
    g1 = Board.step(board)
    assert g1 != g
    assert Board.step(board) == g
    assert Board.generation(board) == 2
  end

  test "cells hold their own state and agree with the board snapshot" do
    {:ok, g} = GameOfLife.centered("glider", 6, 6)
    board = start_board(g)
    snapshot = Board.run(board, 3)
    %{ref: ref} = :sys.get_state(board)

    for pos <- Grid.positions(snapshot) do
      assert Cell.alive?(ref, pos) == Grid.alive?(snapshot, pos)
    end
  end

  test "glider crosses a torus and returns home" do
    {:ok, cells} = Patterns.get("glider")
    g = Grid.new(6, 6, wrap: true) |> Grid.stamp(cells, {1, 1})
    board = start_board(g)
    assert Board.run(board, 24) == g
  end

  test "run/3 invokes the callback once per generation" do
    board = start_board(Grid.new(3, 3))
    parent = self()
    Board.run(board, 4, fn _g, gen -> send(parent, {:gen, gen}) end)
    for gen <- 1..4, do: assert_received({:gen, ^gen})
  end

  test "degenerate grids: 1x1 bounded and tiny tori with repeated neighbours" do
    # A 1x1 bounded cell has zero neighbours and must still complete a step.
    board = start_board(Grid.new(1, 1) |> Grid.put([{0, 0}]))
    assert Grid.population(Board.step(board)) == 0

    # On 1xN and 2x2 tori the same neighbour (or the cell itself) is adjacent
    # more than once. The process version must count multiplicity the same way.
    for {w, h} <- [{1, 1}, {1, 3}, {2, 2}, {2, 3}, {3, 2}] do
      :rand.seed(:exsss, {w, h, 7})
      g = Grid.random(w, h, 0.5, wrap: true)
      board = start_board(g)
      assert Board.run(board, 5).alive == Grid.run(g, 5).alive, "mismatch on #{w}x#{h} torus"
    end
  end

  test "matches the pure reference implementation on random soups" do
    for seed <- 1..6, wrap <- [false, true] do
      :rand.seed(:exsss, {seed, 42, 99})
      w = 5 + rem(seed * 7, 11)
      h = 4 + rem(seed * 5, 9)
      g = Grid.random(w, h, 0.4, wrap: wrap)
      board = start_board(g)

      Enum.reduce(1..15, g, fn gen, expected ->
        expected = Grid.step(expected)
        actual = Board.step(board)
        assert actual.alive == expected.alive, "seed #{seed} wrap=#{wrap} gen #{gen}"
        expected
      end)
    end
  end

  test "several boards run concurrently without interfering" do
    tasks =
      for seed <- 1..8 do
        Task.async(fn ->
          :rand.seed(:exsss, {seed, seed, seed})
          g = Grid.random(12, 12, 0.35, wrap: true)
          {GameOfLife.simulate(g, 10) |> List.last(), Grid.run(g, 10)}
        end)
      end

    for {actual, expected} <- Task.await_many(tasks, 30_000) do
      assert actual.alive == expected.alive
    end
  end

  test "stopping a board terminates its cell processes" do
    board = start_board(Grid.new(4, 4))
    %{sup: sup, ref: ref} = :sys.get_state(board)
    pids = for {_, pid, _, _} <- DynamicSupervisor.which_children(sup), do: pid
    assert length(pids) == 16

    Board.stop(board)
    for pid <- pids, do: refute(Process.alive?(pid))
    # The Registry unregisters dead processes asynchronously (it monitors
    # them), so poll briefly instead of asserting immediately.
    assert eventually(fn -> Registry.lookup(GameOfLife.Registry, {ref, {0, 0}}) == [] end)
  end

  defp eventually(fun, tries \\ 50) do
    cond do
      fun.() -> true
      tries == 0 -> false
      true -> Process.sleep(10) && eventually(fun, tries - 1)
    end
  end
end
