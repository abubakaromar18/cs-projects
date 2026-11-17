defmodule GameOfLife.Board do
  @moduledoc """
  Coordinator for a process-per-cell Game of Life.

  On start it spawns one `GameOfLife.Cell` per grid position under its own
  `DynamicSupervisor`. Each call to `step/1` broadcasts `{:tick, gen}` to every
  cell and replies only when every cell has reported back. This is the
  generation barrier. The board keeps a `MapSet` of live cells built from those
  reports, so reading the grid never needs to query thousands of processes.

  The board is a GenServer. `step/1` is a `call`, but the reply is deferred:
  the board stores `from` and answers with `GenServer.reply/2` once the last
  `:cell_done` message arrives, so the board stays responsive while it waits.
  """
  use GenServer

  alias GameOfLife.{Cell, Grid}

  @default_timeout 30_000

  defstruct [:ref, :sup, :grid, gen: 0, pending: nil, waiting: nil, next_alive: MapSet.new()]

  # ── Public API ─────────────────────────────────────────────────────────────

  @doc "Starts a board from a `Grid`, spawning width × height cell processes."
  @spec start_link(Grid.t(), GenServer.options()) :: GenServer.on_start()
  def start_link(%Grid{} = grid, opts \\ []), do: GenServer.start_link(__MODULE__, grid, opts)

  @doc "Advances one generation and returns the new grid."
  @spec step(GenServer.server(), timeout()) :: Grid.t()
  def step(board, timeout \\ @default_timeout), do: GenServer.call(board, :step, timeout)

  @doc "Advances `n` generations, calling `fun.(grid, gen)` after each one if given."
  @spec run(GenServer.server(), non_neg_integer(), (Grid.t(), non_neg_integer() -> any()) | nil) ::
          Grid.t()
  def run(board, n, fun \\ nil) do
    Enum.reduce(1..n//1, grid(board), fn _, _ ->
      g = step(board)
      if fun, do: fun.(g, generation(board))
      g
    end)
  end

  @doc "The current grid snapshot."
  @spec grid(GenServer.server()) :: Grid.t()
  def grid(board), do: GenServer.call(board, :grid)

  @doc "How many generations have run."
  @spec generation(GenServer.server()) :: non_neg_integer()
  def generation(board), do: GenServer.call(board, :generation)

  @doc "Number of live cell processes under this board."
  @spec process_count(GenServer.server()) :: non_neg_integer()
  def process_count(board), do: GenServer.call(board, :process_count)

  @doc "Stops the board and all of its cells."
  def stop(board), do: GenServer.stop(board)

  # ── GenServer callbacks ────────────────────────────────────────────────────

  @impl true
  def init(%Grid{} = grid) do
    ref = make_ref()
    {:ok, sup} = DynamicSupervisor.start_link(strategy: :one_for_one)

    # Cells are given a dimensions-only grid; they never see the population.
    shape = %{grid | alive: MapSet.new()}

    for pos <- Grid.positions(grid) do
      spec = {Cell, ref: ref, board: self(), grid: shape, pos: pos, alive: Grid.alive?(grid, pos)}

      {:ok, _pid} = DynamicSupervisor.start_child(sup, spec)
    end

    {:ok, %__MODULE__{ref: ref, sup: sup, grid: grid}}
  end

  @impl true
  def handle_call(:step, from, %{waiting: nil} = state) do
    gen = state.gen + 1
    positions = Grid.positions(state.grid)

    for pos <- positions, do: Cell.tick(state.ref, pos, gen)

    {:noreply,
     %{state | gen: gen, waiting: from, pending: length(positions), next_alive: MapSet.new()}}
  end

  def handle_call(:step, _from, state), do: {:reply, {:error, :busy}, state}
  def handle_call(:grid, _from, state), do: {:reply, state.grid, state}
  def handle_call(:generation, _from, state), do: {:reply, state.gen, state}

  def handle_call(:process_count, _from, state),
    do: {:reply, DynamicSupervisor.count_children(state.sup).active, state}

  @impl true
  def handle_info({:cell_done, ref, gen, pos, alive?}, %{ref: ref, gen: gen} = state) do
    next_alive = if alive?, do: MapSet.put(state.next_alive, pos), else: state.next_alive
    state = %{state | pending: state.pending - 1, next_alive: next_alive}

    if state.pending == 0 do
      # Barrier reached: every cell has committed generation `gen`.
      grid = %{state.grid | alive: next_alive}
      GenServer.reply(state.waiting, grid)
      {:noreply, %{state | grid: grid, waiting: nil, pending: nil}}
    else
      {:noreply, state}
    end
  end

  @impl true
  def terminate(_reason, state) do
    if Process.alive?(state.sup), do: DynamicSupervisor.stop(state.sup)
    :ok
  end
end
