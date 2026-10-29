defmodule BankActors.Account do
  @moduledoc """
  One bank account = one process (the actor model).

  The account's balance lives only inside this GenServer. Because a process
  handles its mailbox one message at a time, every deposit and withdrawal is
  applied atomically without any locks — concurrent callers are simply
  serialized by the mailbox.

  Amounts are integers in the smallest currency unit (cents) to avoid
  floating-point rounding errors.

  Processes are registered via `BankActors.Registry` so callers address
  accounts by id instead of pid; the pid changes after a restart, the id
  does not.
  """
  use GenServer, restart: :transient

  alias BankActors.Vault

  @history_limit 50

  defstruct [:id, balance: 0, history: []]

  @type id :: term()
  @type entry :: {:deposit | :withdraw, pos_integer(), non_neg_integer()}
  @type t :: %__MODULE__{id: id(), balance: non_neg_integer(), history: [entry()]}

  # ── Client API ────────────────────────────────────────────────────────

  @doc false
  def start_link({id, initial_balance}) do
    GenServer.start_link(__MODULE__, {id, initial_balance}, name: via(id))
  end

  @doc "Name tuple used to look the account up in the Registry."
  def via(id), do: {:via, Registry, {BankActors.Registry, id}}

  def deposit(id, amount), do: GenServer.call(via(id), {:deposit, amount})
  def withdraw(id, amount), do: GenServer.call(via(id), {:withdraw, amount})
  def balance(id), do: GenServer.call(via(id), :balance)

  @doc "Most recent transactions first: `{kind, amount, balance_after}`."
  def history(id), do: GenServer.call(via(id), :history)

  @doc "Stops the account normally; `:transient` means it is not restarted."
  def close(id), do: GenServer.call(via(id), :close)

  # ── Server callbacks ──────────────────────────────────────────────────

  @impl true
  def init({id, initial_balance}) do
    # Recover from the Vault if we are a restart of a crashed process;
    # otherwise this is a brand-new account.
    state =
      case Vault.fetch(id) do
        %{balance: b, history: h} ->
          %__MODULE__{id: id, balance: b, history: h}

        nil ->
          fresh = %__MODULE__{id: id, balance: initial_balance}
          persist(fresh)
      end

    {:ok, state}
  end

  @impl true
  def handle_call({:deposit, amount}, _from, state) do
    with :ok <- validate(amount) do
      state = state |> apply_change(:deposit, amount) |> persist()
      {:reply, {:ok, state.balance}, state}
    else
      error -> {:reply, error, state}
    end
  end

  def handle_call({:withdraw, amount}, _from, state) do
    cond do
      validate(amount) != :ok ->
        {:reply, {:error, :invalid_amount}, state}

      amount > state.balance ->
        {:reply, {:error, :insufficient_funds}, state}

      true ->
        state = state |> apply_change(:withdraw, amount) |> persist()
        {:reply, {:ok, state.balance}, state}
    end
  end

  def handle_call(:balance, _from, state), do: {:reply, state.balance, state}
  def handle_call(:history, _from, state), do: {:reply, state.history, state}

  def handle_call(:close, _from, state) do
    Vault.delete(state.id)
    {:stop, :normal, {:ok, state.balance}, state}
  end

  # ── Helpers ───────────────────────────────────────────────────────────

  defp validate(amount) when is_integer(amount) and amount > 0, do: :ok
  defp validate(_), do: {:error, :invalid_amount}

  defp apply_change(state, kind, amount) do
    new_balance =
      case kind do
        :deposit -> state.balance + amount
        :withdraw -> state.balance - amount
      end

    history = Enum.take([{kind, amount, new_balance} | state.history], @history_limit)
    %{state | balance: new_balance, history: history}
  end

  # Write-through: save the snapshot, then return the state for piping.
  defp persist(state) do
    Vault.put(state.id, %{balance: state.balance, history: state.history})
    state
  end
end
