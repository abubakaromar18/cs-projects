defmodule BankActors.Vault do
  @moduledoc """
  A tiny durable-ish store for account snapshots, implemented as an `Agent`.

  Each `BankActors.Account` writes its state here after every successful
  operation (write-through). When the supervisor restarts a crashed account,
  the new process reads its last snapshot back, so a crash loses no money.

  This lives in a *separate* process from the accounts on purpose: state
  that must survive a crash cannot be stored in the process that crashes.
  """
  use Agent

  @type snapshot :: %{balance: non_neg_integer(), history: list()}

  def start_link(_opts), do: Agent.start_link(fn -> %{} end, name: __MODULE__)

  @doc "Returns the saved snapshot for `id`, or `nil`."
  @spec fetch(term()) :: snapshot() | nil
  def fetch(id), do: Agent.get(__MODULE__, &Map.get(&1, id))

  @doc "Saves (overwrites) the snapshot for `id`."
  @spec put(term(), snapshot()) :: :ok
  def put(id, snapshot), do: Agent.update(__MODULE__, &Map.put(&1, id, snapshot))

  @doc "Forgets an account entirely (used when it is closed)."
  @spec delete(term()) :: :ok
  def delete(id), do: Agent.update(__MODULE__, &Map.delete(&1, id))
end
