defmodule GameOfLife.Patterns do
  @moduledoc """
  Classic patterns as lists of `{x, y}` offsets from their top-left corner.
  """

  @patterns %{
    # Still lifes
    "block" => ["##", "##"],
    "beehive" => [".##.", "#..#", ".##."],
    # Oscillators
    "blinker" => ["###"],
    "toad" => [".###", "###."],
    "beacon" => ["##..", "##..", "..##", "..##"],
    "pulsar" => [
      "..###...###..",
      ".............",
      "#....#.#....#",
      "#....#.#....#",
      "#....#.#....#",
      "..###...###..",
      ".............",
      "..###...###..",
      "#....#.#....#",
      "#....#.#....#",
      "#....#.#....#",
      ".............",
      "..###...###.."
    ],
    # Spaceships
    "glider" => [".#.", "..#", "###"],
    "lwss" => [".#..#", "#....", "#...#", "####."],
    # Methuselahs
    "r-pentomino" => [".##", "##.", ".#."],
    "acorn" => [".#.....", "...#...", "##..###"]
  }

  @doc "All pattern names, sorted."
  @spec names() :: [String.t()]
  def names, do: @patterns |> Map.keys() |> Enum.sort()

  @doc "Cells of a named pattern, or `:error`."
  @spec get(String.t()) :: {:ok, [{non_neg_integer(), non_neg_integer()}]} | :error
  def get(name) do
    case Map.fetch(@patterns, name) do
      {:ok, rows} -> {:ok, parse(rows)}
      :error -> :error
    end
  end

  @doc "Width and height of a pattern's bounding box."
  @spec size([{integer(), integer()}]) :: {pos_integer(), pos_integer()}
  def size(cells) do
    {xs, ys} = Enum.unzip(cells)
    {Enum.max(xs) + 1, Enum.max(ys) + 1}
  end

  defp parse(rows) do
    for {row, y} <- Enum.with_index(rows),
        {"#", x} <- Enum.with_index(String.graphemes(row)),
        do: {x, y}
  end
end
