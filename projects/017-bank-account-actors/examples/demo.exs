# Run with: mix run examples/demo.exs
#
# Walks through opening accounts, transfers, an overdraft attempt, and a
# deliberate crash that the supervisor recovers from.

money = fn cents -> :io_lib.format("$~.2f", [cents / 100]) |> IO.iodata_to_binary() end

show = fn ->
  for id <- BankActors.accounts() do
    {:ok, bal} = BankActors.balance(id)
    {:ok, pid} = BankActors.lookup(id)

    IO.puts(
      "  #{String.pad_trailing(id, 6)} #{String.pad_leading(money.(bal), 9)}  #{inspect(pid)}"
    )
  end
end

IO.puts("== Opening accounts")
{:ok, _} = BankActors.open_account("alice", 100_00)
{:ok, _} = BankActors.open_account("bob", 25_00)
show.()

IO.puts("\n== alice pays bob $40.00")
:ok = BankActors.transfer("alice", "bob", 40_00)
show.()

IO.puts("\n== bob tries to withdraw $1,000.00")
IO.inspect(BankActors.withdraw("bob", 1_000_00), label: "  result")

IO.puts("\n== Killing alice's process")
{:ok, pid} = BankActors.lookup("alice")
Process.exit(pid, :kill)
Process.sleep(50)
IO.puts("  supervisor restarted it with a new pid; balance recovered from the Vault:")
show.()

IO.puts("\n== alice's history (newest first)")
{:ok, history} = BankActors.history("alice")

Enum.each(history, fn {kind, amt, after_bal} ->
  IO.puts("  #{kind} #{money.(amt)} -> #{money.(after_bal)}")
end)
