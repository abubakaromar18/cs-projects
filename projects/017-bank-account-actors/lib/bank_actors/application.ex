defmodule BankActors.Application do
  @moduledoc """
  OTP application entry point. Builds the supervision tree:

      BankActors.Supervisor (rest_for_one)
      ├── BankActors.Vault              – Agent holding balance snapshots
      ├── BankActors.Registry           – maps account ids to pids
      └── BankActors.AccountSupervisor  – DynamicSupervisor of Account processes

  `:rest_for_one` means: if a child crashes, it and every child started
  *after* it are restarted. If the Registry dies, all accounts restart
  (their names would be stale otherwise), but an account crash never
  touches the Vault or Registry.
  """
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      BankActors.Vault,
      {Registry, keys: :unique, name: BankActors.Registry},
      {DynamicSupervisor, name: BankActors.AccountSupervisor, strategy: :one_for_one}
    ]

    Supervisor.start_link(children, strategy: :rest_for_one, name: BankActors.Supervisor)
  end
end
