defmodule GameOfLife.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      # Unique-key registry mapping {board_ref, {x, y}} to a cell pid. Keying by
      # a per-board ref lets many boards run side by side (e.g. async tests).
      {Registry, keys: :unique, name: GameOfLife.Registry, partitions: System.schedulers_online()}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: GameOfLife.Supervisor)
  end
end
