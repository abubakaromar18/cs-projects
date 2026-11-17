defmodule Mix.Tasks.Life do
  @shortdoc "Runs the process-per-cell Game of Life in the terminal"
  @moduledoc """
  Runs Conway's Game of Life with one process per cell and prints each
  generation as ASCII.

      mix life [options]

  ## Options

    * `--pattern NAME`  a built-in pattern (default: glider). Use `--list` to see them.
    * `--file PATH`     load a plain-text pattern (`#`/`O` live, `.` dead)
    * `--random`        random soup instead of a pattern
    * `--density F`     live-cell chance for `--random` (default: 0.35)
    * `--seed N`        RNG seed for `--random`
    * `--width N`, `--height N`  grid size (default: 20 × 12)
    * `--gens N`        generations to run (default: 30)
    * `--wrap`          toroidal edges
    * `--delay MS`      pause between frames and redraw in place (default: 0, print all frames)
    * `--verify`        check every generation against the pure `Grid.step/1`
    * `--list`          list built-in patterns and exit
  """
  use Mix.Task

  alias GameOfLife.{Board, Grid, Patterns}

  @switches [
    pattern: :string,
    file: :string,
    random: :boolean,
    density: :float,
    seed: :integer,
    width: :integer,
    height: :integer,
    gens: :integer,
    wrap: :boolean,
    delay: :integer,
    verify: :boolean,
    list: :boolean
  ]

  @impl Mix.Task
  def run(argv) do
    Mix.Task.run("app.start")
    {opts, _rest, invalid} = OptionParser.parse(argv, strict: @switches)

    if invalid != [], do: Mix.raise("invalid options: #{inspect(invalid)}")

    if opts[:list] do
      Enum.each(Patterns.names(), &Mix.shell().info/1)
    else
      opts |> build_grid() |> simulate(opts)
    end
  end

  defp build_grid(opts) do
    w = Keyword.get(opts, :width, 20)
    h = Keyword.get(opts, :height, 12)
    grid_opts = [wrap: Keyword.get(opts, :wrap, false)]

    cond do
      opts[:file] ->
        opts[:file] |> File.read!() |> Grid.from_string(grid_opts)

      opts[:random] ->
        if seed = opts[:seed], do: :rand.seed(:exsss, {seed, seed, seed})
        Grid.random(w, h, Keyword.get(opts, :density, 0.35), grid_opts)

      true ->
        case GameOfLife.centered(Keyword.get(opts, :pattern, "glider"), w, h, grid_opts) do
          {:ok, g} -> g
          {:error, msg} -> Mix.raise(msg)
        end
    end
  end

  defp simulate(grid, opts) do
    gens = Keyword.get(opts, :gens, 30)
    delay = Keyword.get(opts, :delay, 0)
    verify? = Keyword.get(opts, :verify, false)

    {:ok, board} = Board.start_link(grid)
    procs = Board.process_count(board)
    {micros, final} = :timer.tc(fn -> loop(board, grid, 0, gens, delay, verify?) end)
    Board.stop(board)

    Mix.shell().info(
      "\n#{procs} cell processes · #{gens} generations · final population #{Grid.population(final)}" <>
        " · #{Float.round(micros / 1000, 1)} ms" <> if(verify?, do: " · verified ✓", else: "")
    )
  end

  defp loop(board, grid, gen, gens, delay, verify?) do
    draw(grid, gen, delay)
    if delay > 0, do: Process.sleep(delay)

    if gen == gens do
      grid
    else
      next = Board.step(board)

      if verify? and next.alive != Grid.step(grid).alive do
        Mix.raise("generation #{gen + 1}: process board disagrees with reference implementation")
      end

      loop(board, next, gen + 1, gens, delay, verify?)
    end
  end

  # With a delay we redraw in place using ANSI "cursor home + clear screen".
  defp draw(grid, gen, delay) do
    if delay > 0, do: IO.write("\e[H\e[2J")
    IO.puts("gen #{gen}  pop #{Grid.population(grid)}")
    IO.puts(Grid.to_string(grid, "█", "·"))
    if delay == 0, do: IO.puts("")
  end
end
