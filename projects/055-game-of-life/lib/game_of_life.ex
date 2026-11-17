defmodule GameOfLife do
  @moduledoc """
  Conway's Game of Life where every cell is its own BEAM process.

  Quick start:

      iex> {:ok, cells} = GameOfLife.Patterns.get("blinker")
      iex> grid = GameOfLife.Grid.new(5, 5) |> GameOfLife.Grid.stamp(cells, {1, 2})
      iex> {:ok, board} = GameOfLife.Board.start_link(grid)
      iex> GameOfLife.Board.step(board) |> GameOfLife.Grid.to_string()
      ".....\\n..#..\\n..#..\\n..#..\\n....."
      iex> GameOfLife.Board.stop(board)
      :ok

  See `GameOfLife.Grid` for the pure reference implementation,
  `GameOfLife.Cell` for the per-cell protocol and `GameOfLife.Board` for the
  generation barrier.
  """

  alias GameOfLife.{Board, Grid, Patterns}

  @doc """
  Builds a grid of the given size with a named pattern centred on it.
  """
  @spec centered(String.t(), pos_integer(), pos_integer(), keyword()) ::
          {:ok, Grid.t()} | {:error, String.t()}
  def centered(name, width, height, opts \\ []) do
    with {:ok, cells} <- fetch_pattern(name),
         {pw, ph} = Patterns.size(cells),
         :ok <- fits(pw, ph, width, height) do
      origin = {div(width - pw, 2), div(height - ph, 2)}
      {:ok, Grid.new(width, height, opts) |> Grid.stamp(cells, origin)}
    end
  end

  @doc """
  Runs `grid` for `gens` generations on a process-per-cell board and returns
  the list of grids, starting with generation 0.
  """
  @spec simulate(Grid.t(), non_neg_integer()) :: [Grid.t()]
  def simulate(%Grid{} = grid, gens) do
    {:ok, board} = Board.start_link(grid)

    try do
      [grid | Enum.map(1..gens//1, fn _ -> Board.step(board) end)]
    after
      Board.stop(board)
    end
  end

  defp fetch_pattern(name) do
    case Patterns.get(name) do
      {:ok, cells} ->
        {:ok, cells}

      :error ->
        {:error,
         "unknown pattern #{inspect(name)}; try one of: #{Enum.join(Patterns.names(), ", ")}"}
    end
  end

  defp fits(pw, ph, w, h) when pw <= w and ph <= h, do: :ok
  defp fits(pw, ph, w, h), do: {:error, "pattern is #{pw}x#{ph} but the grid is only #{w}x#{h}"}
end
