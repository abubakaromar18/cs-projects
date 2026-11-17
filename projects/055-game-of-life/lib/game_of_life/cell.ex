defmodule GameOfLife.Cell do
  @moduledoc """
  One cell = one BEAM process.

  A cell knows only its own state and the *addresses* of its neighbours. It
  has no view of the board. Each generation runs as a small message protocol:

      Board ──{:tick, gen}──▶ Cell
      Cell  ──{:neighbor, gen, alive?}──▶ each neighbour       (gossip)
      Cell  ◀──{:neighbor, gen, alive?}── each neighbour
      Cell  ──{:cell_done, ref, gen, pos, alive?}──▶ Board     (once all heard)

  Messages are asynchronous and their order is not guaranteed, so a
  neighbour's gossip for generation `gen` can arrive *before* this cell has
  received its own `{:tick, gen}`. The cell therefore buffers gossip per
  generation in an inbox (`%{gen => {heard, live}}`) and only computes the next
  state once it has (a) been ticked and (b) heard from every neighbour.

  Because the board only starts generation `gen + 1` after every cell has
  reported `gen`, no cell can ever be more than one generation ahead of any
  other. This is a barrier synchronisation.
  """
  use GenServer, restart: :temporary

  alias GameOfLife.Grid

  defstruct [:ref, :board, :pos, :alive, :neighbors, :expected, ticked: nil, inbox: %{}]

  @doc """
  Options:

    * `:ref` – a unique reference identifying the board (the Registry namespace)
    * `:board` – pid that receives `:cell_done` reports
    * `:grid` – a `Grid` describing the dimensions and topology
    * `:pos` – this cell's `{x, y}`
    * `:alive` – initial state
  """
  def start_link(opts) do
    ref = Keyword.fetch!(opts, :ref)
    pos = Keyword.fetch!(opts, :pos)
    GenServer.start_link(__MODULE__, opts, name: via(ref, pos))
  end

  @doc "The Registry name of the cell at `pos` on board `ref`."
  def via(ref, pos), do: {:via, Registry, {GameOfLife.Registry, {ref, pos}}}

  @doc "Starts generation `gen` on this cell."
  def tick(ref, pos, gen), do: GenServer.cast(via(ref, pos), {:tick, gen})

  @doc "Reads the cell's current state (used for debugging and tests)."
  def alive?(ref, pos), do: GenServer.call(via(ref, pos), :alive?)

  @impl true
  def init(opts) do
    grid = Keyword.fetch!(opts, :grid)
    pos = Keyword.fetch!(opts, :pos)
    # Duplicates are kept on purpose: on a tiny torus the same neighbour can be
    # adjacent twice and must be counted twice. The relation is symmetric with
    # multiplicity, so each cell receives exactly `length(neighbors)` messages.
    neighbors = Grid.neighbors(grid, pos)

    state = %__MODULE__{
      ref: Keyword.fetch!(opts, :ref),
      board: Keyword.fetch!(opts, :board),
      pos: pos,
      alive: Keyword.get(opts, :alive, false),
      neighbors: neighbors,
      expected: length(neighbors)
    }

    {:ok, state}
  end

  @impl true
  def handle_cast({:tick, gen}, %{ticked: nil} = state) do
    # Gossip our *current* state to every neighbour, tagged with the generation.
    for n <- state.neighbors do
      GenServer.cast(via(state.ref, n), {:neighbor, gen, state.alive})
    end

    maybe_advance(%{state | ticked: gen})
  end

  def handle_cast({:neighbor, gen, alive?}, state) do
    inbox =
      Map.update(state.inbox, gen, {1, bool_to_int(alive?)}, fn {heard, live} ->
        {heard + 1, live + bool_to_int(alive?)}
      end)

    maybe_advance(%{state | inbox: inbox})
  end

  @impl true
  def handle_call(:alive?, _from, state), do: {:reply, state.alive, state}

  # Computes the next state once ticked and all neighbours have reported.
  defp maybe_advance(%{ticked: nil} = state), do: {:noreply, state}

  defp maybe_advance(%{ticked: gen, expected: expected} = state) do
    case Map.get(state.inbox, gen, {0, 0}) do
      {^expected, live} ->
        next = Grid.rule(state.alive, live)
        send(state.board, {:cell_done, state.ref, gen, state.pos, next})
        {:noreply, %{state | alive: next, ticked: nil, inbox: Map.delete(state.inbox, gen)}}

      _not_yet ->
        {:noreply, state}
    end
  end

  defp bool_to_int(true), do: 1
  defp bool_to_int(false), do: 0
end
