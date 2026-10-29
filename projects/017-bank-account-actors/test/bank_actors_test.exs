defmodule BankActorsTest do
  # Not async: all tests share the application's global supervision tree.
  use ExUnit.Case, async: false

  # Each test gets unique account ids so state never leaks between tests.
  defp uid(name), do: "#{name}-#{System.unique_integer([:positive])}"

  describe "opening accounts" do
    test "starts with the given balance" do
      id = uid("alice")
      assert {:ok, ^id} = BankActors.open_account(id, 1_000)
      assert {:ok, 1_000} = BankActors.balance(id)
      assert id in BankActors.accounts()
    end

    test "defaults to zero" do
      id = uid("zero")
      {:ok, _} = BankActors.open_account(id)
      assert {:ok, 0} = BankActors.balance(id)
    end

    test "rejects duplicate ids and negative balances" do
      id = uid("dup")
      {:ok, _} = BankActors.open_account(id, 5)
      assert {:error, :already_exists} = BankActors.open_account(id, 5)
      assert {:error, :invalid_amount} = BankActors.open_account(uid("neg"), -1)
    end
  end

  describe "deposits and withdrawals" do
    setup do
      id = uid("acct")
      {:ok, _} = BankActors.open_account(id, 100)
      %{id: id}
    end

    test "deposit increases the balance", %{id: id} do
      assert {:ok, 150} = BankActors.deposit(id, 50)
    end

    test "withdraw decreases the balance", %{id: id} do
      assert {:ok, 70} = BankActors.withdraw(id, 30)
    end

    test "cannot overdraw", %{id: id} do
      assert {:error, :insufficient_funds} = BankActors.withdraw(id, 101)
      assert {:ok, 100} = BankActors.balance(id)
    end

    test "rejects non-positive and non-integer amounts", %{id: id} do
      for bad <- [0, -5, 1.5, "10", nil] do
        assert {:error, :invalid_amount} = BankActors.deposit(id, bad)
        assert {:error, :invalid_amount} = BankActors.withdraw(id, bad)
      end

      assert {:ok, 100} = BankActors.balance(id)
    end

    test "records history newest first", %{id: id} do
      BankActors.deposit(id, 10)
      BankActors.withdraw(id, 5)
      assert {:ok, [{:withdraw, 5, 105}, {:deposit, 10, 110}]} = BankActors.history(id)
    end
  end

  describe "unknown accounts" do
    test "return :not_found instead of crashing the caller" do
      missing = uid("ghost")
      assert {:error, :not_found} = BankActors.balance(missing)
      assert {:error, :not_found} = BankActors.deposit(missing, 1)
      assert {:error, :not_found} = BankActors.withdraw(missing, 1)
      assert {:error, :not_found} = BankActors.close_account(missing)
    end
  end

  describe "transfers" do
    setup do
      a = uid("from")
      b = uid("to")
      {:ok, _} = BankActors.open_account(a, 500)
      {:ok, _} = BankActors.open_account(b, 0)
      %{a: a, b: b}
    end

    test "moves money between accounts", %{a: a, b: b} do
      assert :ok = BankActors.transfer(a, b, 200)
      assert {:ok, 300} = BankActors.balance(a)
      assert {:ok, 200} = BankActors.balance(b)
    end

    test "fails cleanly on insufficient funds", %{a: a, b: b} do
      assert {:error, :insufficient_funds} = BankActors.transfer(a, b, 501)
      assert {:ok, 500} = BankActors.balance(a)
      assert {:ok, 0} = BankActors.balance(b)
    end

    test "fails without withdrawing when the destination is missing", %{a: a} do
      assert {:error, :not_found} = BankActors.transfer(a, uid("nobody"), 10)
      assert {:ok, 500} = BankActors.balance(a)
    end

    test "rejects transfers to the same account", %{a: a} do
      assert {:error, :same_account} = BankActors.transfer(a, a, 10)
    end

    test "concurrent transfers conserve the total", %{a: a, b: b} do
      # 100 tasks shuffle money back and forth; some will fail for lack of
      # funds, but no cent may be created or destroyed.
      1..100
      |> Enum.map(fn i ->
        Task.async(fn ->
          if rem(i, 2) == 0, do: BankActors.transfer(a, b, 7), else: BankActors.transfer(b, a, 3)
        end)
      end)
      |> Enum.each(&Task.await/1)

      {:ok, ba} = BankActors.balance(a)
      {:ok, bb} = BankActors.balance(b)
      assert ba + bb == 500
    end
  end

  describe "concurrency" do
    test "parallel deposits are serialized by the mailbox (no lost updates)" do
      id = uid("busy")
      {:ok, _} = BankActors.open_account(id, 0)

      1..1_000
      |> Task.async_stream(fn _ -> BankActors.deposit(id, 1) end, max_concurrency: 50)
      |> Stream.run()

      assert {:ok, 1_000} = BankActors.balance(id)
    end
  end

  describe "supervision" do
    test "a crashed account is restarted with its balance recovered" do
      id = uid("crash")
      {:ok, _} = BankActors.open_account(id, 1_000)
      {:ok, 1_250} = BankActors.deposit(id, 250)
      {:ok, old_pid} = BankActors.lookup(id)

      ref = Process.monitor(old_pid)
      Process.exit(old_pid, :kill)
      assert_receive {:DOWN, ^ref, :process, ^old_pid, :killed}

      new_pid = wait_for_restart(id, old_pid)
      assert new_pid != old_pid
      assert {:ok, 1_250} = BankActors.balance(id)
      assert {:ok, [{:deposit, 250, 1_250}]} = BankActors.history(id)
    end

    test "one account crashing does not affect others" do
      victim = uid("victim")
      bystander = uid("bystander")
      {:ok, _} = BankActors.open_account(victim, 1)
      {:ok, _} = BankActors.open_account(bystander, 42)
      {:ok, bystander_pid} = BankActors.lookup(bystander)
      {:ok, victim_pid} = BankActors.lookup(victim)

      Process.exit(victim_pid, :kill)
      wait_for_restart(victim, victim_pid)

      assert {:ok, ^bystander_pid} = BankActors.lookup(bystander)
      assert {:ok, 42} = BankActors.balance(bystander)
    end

    test "closed accounts are not restarted and their snapshot is dropped" do
      id = uid("closing")
      {:ok, _} = BankActors.open_account(id, 99)
      {:ok, pid} = BankActors.lookup(id)
      ref = Process.monitor(pid)

      assert {:ok, 99} = BankActors.close_account(id)
      assert_receive {:DOWN, ^ref, :process, ^pid, :normal}
      # Registry cleanup is asynchronous; give it a moment.
      Process.sleep(20)

      assert {:error, :not_found} = BankActors.balance(id)
      assert BankActors.Vault.fetch(id) == nil
      # Reopening starts fresh rather than reviving the old balance.
      {:ok, _} = BankActors.open_account(id, 1)
      assert {:ok, 1} = BankActors.balance(id)
    end
  end

  # Poll the Registry until the supervisor has registered a new pid.
  defp wait_for_restart(id, old_pid, attempts \\ 100) do
    case BankActors.lookup(id) do
      {:ok, pid} when pid != old_pid ->
        pid

      _ when attempts > 0 ->
        Process.sleep(5)
        wait_for_restart(id, old_pid, attempts - 1)

      _ ->
        flunk("account #{inspect(id)} was not restarted")
    end
  end
end
