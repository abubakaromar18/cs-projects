defmodule GameOfLife.GridTest do
  use ExUnit.Case, async: true
  doctest GameOfLife.Grid

  alias GameOfLife.{Grid, Patterns}

  defp grid(text, opts \\ []), do: Grid.from_string(text, opts)

  describe "rule/2 (B3/S23)" do
    test "birth on exactly three" do
      assert Grid.rule(false, 3)
      for n <- [0, 1, 2, 4, 5, 6, 7, 8], do: refute(Grid.rule(false, n))
    end

    test "survival on two or three" do
      assert Grid.rule(true, 2)
      assert Grid.rule(true, 3)
      for n <- [0, 1, 4, 5, 6, 7, 8], do: refute(Grid.rule(true, n))
    end
  end

  describe "parsing and rendering" do
    test "round-trips text" do
      text = ".#.\n..#\n###"
      assert text |> grid() |> Grid.to_string() == text
    end

    test "pads ragged lines and ignores a trailing newline" do
      g = grid("#\n.##\n")
      assert {g.width, g.height} == {3, 2}
      assert Grid.to_string(g) == "#..\n.##"
    end

    test "rejects out-of-bounds cells on a bounded grid" do
      assert_raise ArgumentError, fn -> Grid.new(3, 3) |> Grid.put([{3, 0}]) end
    end

    test "wraps out-of-bounds cells on a torus" do
      g = Grid.new(3, 3, wrap: true) |> Grid.put([{-1, 4}])
      assert Grid.alive?(g, {2, 1})
    end
  end

  describe "neighbors/2" do
    test "interior, edge and corner on a bounded grid" do
      g = Grid.new(5, 5)
      assert length(Grid.neighbors(g, {2, 2})) == 8
      assert length(Grid.neighbors(g, {0, 2})) == 5
      assert length(Grid.neighbors(g, {0, 0})) == 3
    end

    test "every cell has 8 neighbours on a torus" do
      g = Grid.new(4, 4, wrap: true)
      for pos <- Grid.positions(g), do: assert(length(Grid.neighbors(g, pos)) == 8)
      assert {3, 3} in Grid.neighbors(g, {0, 0})
    end
  end

  describe "step/1 with known patterns" do
    test "block is a still life" do
      g = grid("....\n.##.\n.##.\n....")
      assert Grid.step(g) == g
    end

    test "blinker has period 2" do
      g = grid(".....\n.....\n.###.\n.....\n.....")
      vertical = grid(".....\n..#..\n..#..\n..#..\n.....")
      assert Grid.step(g) == vertical
      assert Grid.run(g, 2) == g
    end

    test "beacon and toad have period 2, pulsar period 3" do
      for {name, period, size} <- [{"beacon", 2, 6}, {"toad", 2, 6}, {"pulsar", 3, 17}] do
        {:ok, g} = GameOfLife.centered(name, size, size)
        refute Grid.step(g) == g, "#{name} should change"
        assert Grid.run(g, period) == g, "#{name} should have period #{period}"
      end
    end

    test "glider moves one cell diagonally every 4 generations on a torus" do
      {:ok, cells} = Patterns.get("glider")
      g = Grid.new(8, 8, wrap: true) |> Grid.stamp(cells, {0, 0})
      shifted = Grid.new(8, 8, wrap: true) |> Grid.stamp(cells, {1, 1})
      assert Grid.run(g, 4) == shifted
      # After 32 generations it has crossed the whole 8x8 torus.
      assert Grid.run(g, 32) == g
    end

    test "a lone cell or pair dies" do
      assert Grid.population(Grid.step(grid("...\n.#.\n..."))) == 0
      assert Grid.population(Grid.step(grid("....\n.##.\n...."))) == 0
    end

    test "glider dies against a bounded corner (becomes a block)" do
      {:ok, cells} = Patterns.get("glider")
      g = Grid.new(6, 6) |> Grid.stamp(cells, {0, 0}) |> Grid.run(40)
      assert Grid.population(g) == 4
      assert Grid.step(g) == g
    end
  end

  describe "patterns" do
    test "every pattern parses and has a sane size" do
      for name <- Patterns.names() do
        {:ok, cells} = Patterns.get(name)
        assert cells != []
        {w, h} = Patterns.size(cells)
        assert w > 0 and h > 0
      end

      assert Patterns.get("nope") == :error
    end

    test "centered/4 reports a pattern that does not fit" do
      assert {:error, msg} = GameOfLife.centered("pulsar", 5, 5)
      assert msg =~ "13x13"
      assert {:error, _} = GameOfLife.centered("nope", 5, 5)
    end
  end
end
