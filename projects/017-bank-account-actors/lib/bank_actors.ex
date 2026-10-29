defmodule BankActors do
  @moduledoc """
  Public API for the bank. Every account is its own supervised process.

      iex> BankActors.open_account("alice", 10_000)
      {:ok, "alice"}
      iex> BankActors.deposit("alice", 2_500)
      {:ok, 12_500}

  All functions return `{:error, :not_found}` for unknown accounts instead of
  crashing the caller.
  """

  alias BankActors.Account

  @type id :: term()
  @type error :: {:error, :not_found | :invalid_amount | :insufficient_funds | atom()}

  @doc "Opens a new account with an optional starting balance (in cents)."
  @spec open_account(id(), non_neg_integer()) :: {:ok, id()} | error()
  def open_account(id, initial_balance \\ 0)

  def open_account(id, initial_balance)
      when is_integer(initial_balance) and initial_balance >= 0 do
    spec = {Account, {id, initial_balance}}

    case DynamicSupervisor.start_child(BankActors.AccountSupervisor, spec) do
      {:ok, _pid} -> {:ok, id}
      {:error, {:already_started, _pid}} -> {:error, :already_exists}
      {:error, reason} -> {:error, reason}
    end
  end

  def open_account(_id, _bad), do: {:error, :invalid_amount}

  @spec deposit(id(), pos_integer()) :: {:ok, non_neg_integer()} | error()
  def deposit(id, amount), do: safely(id, fn -> Account.deposit(id, amount) end)

  @spec withdraw(id(), pos_integer()) :: {:ok, non_neg_integer()} | error()
  def withdraw(id, amount), do: safely(id, fn -> Account.withdraw(id, amount) end)

  @spec balance(id()) :: {:ok, non_neg_integer()} | error()
  def balance(id), do: safely(id, fn -> {:ok, Account.balance(id)} end)

  @spec history(id()) :: {:ok, list()} | error()
  def history(id), do: safely(id, fn -> {:ok, Account.history(id)} end)

  @doc "Closes the account and returns its final balance."
  @spec close_account(id()) :: {:ok, non_neg_integer()} | error()
  def close_account(id), do: safely(id, fn -> Account.close(id) end)

  @doc """
  Moves `amount` from one account to another.

  Two independent actors cannot be updated in one atomic step, so this is a
  tiny saga: withdraw first (which can fail cleanly), then deposit. If the
  deposit fails, the withdrawal is compensated by refunding the source.
  """
  @spec transfer(id(), id(), pos_integer()) :: :ok | error()
  def transfer(from, to, _amount) when from == to, do: {:error, :same_account}

  def transfer(from, to, amount) do
    with {:ok, _} <- lookup(to),
         {:ok, _} <- withdraw(from, amount) do
      case deposit(to, amount) do
        {:ok, _} ->
          :ok

        error ->
          # Compensating action: put the money back.
          {:ok, _} = deposit(from, amount)
          error
      end
    end
  end

  @doc "Ids of all open accounts."
  @spec accounts() :: [id()]
  def accounts do
    Registry.select(BankActors.Registry, [{{:"$1", :_, :_}, [], [:"$1"]}]) |> Enum.sort()
  end

  @doc "Current pid for an account (changes after a supervised restart)."
  @spec lookup(id()) :: {:ok, pid()} | {:error, :not_found}
  def lookup(id) do
    case Registry.lookup(BankActors.Registry, id) do
      [{pid, _}] -> {:ok, pid}
      [] -> {:error, :not_found}
    end
  end

  # A call to an unregistered via-name exits the caller; turn that into
  # an error tuple so client code never crashes because of a bad id.
  defp safely(id, fun) do
    case lookup(id) do
      {:ok, _} ->
        try do
          fun.()
        catch
          :exit, {:noproc, _} -> {:error, :not_found}
          :exit, {:normal, _} -> {:error, :not_found}
        end

      error ->
        error
    end
  end
end
