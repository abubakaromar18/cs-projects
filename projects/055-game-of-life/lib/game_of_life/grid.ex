defmodule GameOfLife.Grid do
  @moduledoc """
  A pure, immutable Game of Life grid. It is the reference implementation:
  the process-per-cell `GameOfLife.Board` is tested against it.

  Live cells are kept in a `MapSet` of `{x, y}` tuples (sparse storage), so
  memory use is proportional to the population, not the area.

  Two topologies are supported:

    * `wrap: false` (default): a bounded plane. Cells past the edge are dead.
    * `wrap: true`: a torus. The left edge touches the right, the top the bottom.
  """

  @enforce_keys [:width, :height]
  defstruct width: 0, height: 0, wrap: false, alive: MapSet.new()

  @type pos :: {non_neg_integer(), non_neg_integer()}
  @type t :: %__MODULE__{
          width: pos_integer(),
          height: pos_integer(),
          wrap: boolean(),
          alive: MapSet.t(pos)
        }

  @offsets for dx <- -1..1, dy <- -1..1, {dx, dy} != {0, 0}, do: {dx, dy}

  @doc "Creates an empty grid."
  @spec new(pos_integer(), pos_integer(), keyword()) :: t
  def new(width, height, opts \\ []) when width > 0 and height > 0 do
    %__MODULE__{width: width, height: height, wrap: Keyword.get(opts, :wrap, false)}
  end

  @doc """
  Parses a grid from text. `#` or `O` is a live cell, `.` or a space is dead.
  The width is the longest line; shorter lines are padded with dead cells.

      iex> g = GameOfLife.Grid.from_string(".#.\\n.#.\\n.#.")
      iex> GameOfLife.Grid.population(g)
      3
  """
  @spec from_string(String.t(), keyword()) :: t
  def from_string(text, opts \\ []) do
    lines =
      text
      |> String.split("\n")
      |> Enum.map(&String.trim_trailing(&1, "\r"))
      |> drop_trailing_blank()

    height = max(length(lines), 1)
    width = lines |> Enum.map(&String.length/1) |> Enum.max(fn -> 1 end) |> max(1)

    alive =
      for {line, y} <- Enum.with_index(lines),
          {ch, x} <- Enum.with_index(String.graphemes(line)),
          ch in ["#", "O", "o", "*"],
          into: MapSet.new(),
          do: {x, y}

    %{new(width, height, opts) | alive: alive}
  end

  defp drop_trailing_blank(lines) do
    lines |> Enum.reverse() |> Enum.drop_while(&(&1 == "")) |> Enum.reverse()
  end

  @doc "Renders the grid as text, one row per line."
  @spec to_string(t, String.t(), String.t()) :: String.t()
  def to_string(%__MODULE__{} = g, live \\ "#", dead \\ ".") do
    Enum.map_join(0..(g.height - 1), "\n", fn y ->
      Enum.map_join(0..(g.width - 1), fn x -> if alive?(g, {x, y}), do: live, else: dead end)
    end)
  end

  @doc "Places live cells. Positions outside a bounded grid are rejected."
  @spec put(t, [pos] | MapSet.t(pos)) :: t
  def put(%__MODULE__{} = g, cells) do
    Enum.reduce(cells, g, fn pos, acc ->
      pos = normalize!(acc, pos)
      %{acc | alive: MapSet.put(acc.alive, pos)}
    end)
  end

  @doc "Stamps a pattern (a list of positions) with its top-left corner at `{ox, oy}`."
  @spec stamp(t, [pos], pos) :: t
  def stamp(g, pattern, {ox, oy}),
    do: put(g, Enum.map(pattern, fn {x, y} -> {x + ox, y + oy} end))

  @doc "Fills the grid at random. `density` is the chance each cell is alive."
  @spec random(pos_integer(), pos_integer(), float(), keyword()) :: t
  def random(width, height, density \\ 0.35, opts \\ []) do
    g = new(width, height, opts)

    alive =
      for x <- 0..(width - 1),
          y <- 0..(height - 1),
          :rand.uniform() < density,
          into: MapSet.new(),
          do: {x, y}

    %{g | alive: alive}
  end

  @spec alive?(t, pos) :: boolean()
  def alive?(%__MODULE__{alive: alive}, pos), do: MapSet.member?(alive, pos)

  @spec population(t) :: non_neg_integer()
  def population(%__MODULE__{alive: alive}), do: MapSet.size(alive)

  @doc "Every position on the grid, row by row."
  @spec positions(t) :: [pos]
  def positions(%__MODULE__{width: w, height: h}) do
    for y <- 0..(h - 1), x <- 0..(w - 1), do: {x, y}
  end

  @doc """
  The Moore neighbourhood of `pos`: up to 8 surrounding positions.
  On a bounded grid, edge cells have fewer. On a tiny torus a neighbour can
  appear twice (e.g. width 2), and it is then counted twice, which is the
  standard toroidal definition.
  """
  @spec neighbors(t, pos) :: [pos]
  def neighbors(%__MODULE__{} = g, {x, y}) do
    @offsets
    |> Enum.map(fn {dx, dy} -> {x + dx, y + dy} end)
    |> Enum.flat_map(fn p ->
      case wrap_pos(g, p) do
        nil -> []
        p -> [p]
      end
    end)
  end

  @doc "The B3/S23 rule: the next state of one cell given its live neighbour count."
  @spec rule(boolean(), non_neg_integer()) :: boolean()
  def rule(true, n) when n in [2, 3], do: true
  def rule(false, 3), do: true
  def rule(_alive, _n), do: false

  @doc """
  Advances one generation.

  Only live cells and their neighbours can change, so we count neighbours by
  scattering a +1 from each live cell into a frequency map. That is
  O(population) instead of O(width * height).
  """
  @spec step(t) :: t
  def step(%__MODULE__{} = g) do
    counts =
      Enum.reduce(g.alive, %{}, fn pos, acc ->
        Enum.reduce(neighbors(g, pos), acc, fn n, acc -> Map.update(acc, n, 1, &(&1 + 1)) end)
      end)

    alive = for {pos, n} <- counts, rule(alive?(g, pos), n), into: MapSet.new(), do: pos

    %{g | alive: alive}
  end

  @doc "Advances `n` generations."
  @spec run(t, non_neg_integer()) :: t
  def run(g, 0), do: g
  def run(g, n) when n > 0, do: g |> step() |> run(n - 1)

  # Maps a raw coordinate onto the grid, or nil if it falls off a bounded edge.
  defp wrap_pos(%__MODULE__{wrap: true, width: w, height: h}, {x, y}),
    do: {Integer.mod(x, w), Integer.mod(y, h)}

  defp wrap_pos(%__MODULE__{width: w, height: h}, {x, y})
       when x >= 0 and y >= 0 and x < w and y < h,
       do: {x, y}

  defp wrap_pos(_g, _pos), do: nil

  defp normalize!(g, pos) do
    case wrap_pos(g, pos) do
      nil ->
        raise ArgumentError, "position #{inspect(pos)} is outside a #{g.width}x#{g.height} grid"

      p ->
        p
    end
  end
end
