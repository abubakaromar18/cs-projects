# 017 · Bank Account Actors

A small bank built on Elixir/OTP where **every account is its own process**. Accounts are `GenServer`s started under a `DynamicSupervisor`, found by id through a `Registry`, and backed by a snapshot store so a crashed account comes back with its balance intact.

**Level:** Starter · **Area:** Functional & Polyglot

## Features

- Open, deposit, withdraw, transfer, check balance and history, close.
- Integer cents everywhere, so no floating-point rounding.
- Clear error tuples (`:insufficient_funds`, `:invalid_amount`, `:not_found`, `:already_exists`, `:same_account`) instead of crashes.
- Kill any account process and the supervisor restarts it with the same balance and history.

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Actor model.** State lives inside a process and changes only through messages. | `BankActors.Account` |
| **Mailbox serialization.** One message at a time means no locks and no lost updates, even with 1,000 concurrent deposits. | `handle_call/3`, concurrency test |
| **Supervision trees and "let it crash".** Failures are isolated and restarted, not defensively caught. | `BankActors.Application` |
| **Restart strategies.** `:rest_for_one` at the top; `:transient` children so a normal close is not restarted. | `application.ex`, `account.ex` |
| **Process registry / location transparency.** Callers use ids; pids change after a restart. | `Account.via/1`, `BankActors.lookup/1` |
| **Write-through state recovery.** Snapshots live in a separate process so they survive the crash. | `BankActors.Vault` |
| **Sagas and compensating actions.** A transfer across two actors is withdraw → deposit, refunding on failure. | `BankActors.transfer/3` |
| **Pattern matching and `with` pipelines.** Errors flow as tagged tuples. | throughout |

## Project structure

```
lib/
  bank_actors.ex              public API (open, deposit, withdraw, transfer, ...)
  bank_actors/application.ex  supervision tree
  bank_actors/account.ex      the account GenServer
  bank_actors/vault.ex        Agent holding balance snapshots
test/bank_actors_test.exs     18 ExUnit tests
examples/demo.exs             scripted walkthrough
```

Supervision tree:

```
BankActors.Supervisor (rest_for_one)
├── BankActors.Vault
├── BankActors.Registry
└── BankActors.AccountSupervisor (DynamicSupervisor)
    ├── Account "alice"
    └── Account "bob"
```

## Build, run, test

Requires Elixir 1.14+ (no external dependencies).

```bash
mix compile
mix test                     # 18 tests
mix run examples/demo.exs    # walkthrough
iex -S mix                   # play interactively
```

## Example

```elixir
iex> BankActors.open_account("alice", 100_00)
{:ok, "alice"}
iex> BankActors.open_account("bob")
{:ok, "bob"}
iex> BankActors.transfer("alice", "bob", 40_00)
:ok
iex> BankActors.withdraw("bob", 1_000_00)
{:error, :insufficient_funds}
iex> {:ok, pid} = BankActors.lookup("alice"); Process.exit(pid, :kill)
iex> BankActors.balance("alice")      # restarted, balance recovered
{:ok, 6000}
```

Demo output:

```
== Opening accounts
  alice    $100.00  #PID<0.148.0>
  bob       $25.00  #PID<0.149.0>

== alice pays bob $40.00
  alice     $60.00  #PID<0.148.0>
  bob       $65.00  #PID<0.149.0>

== bob tries to withdraw $1,000.00
  result: {:error, :insufficient_funds}

== Killing alice's process
  supervisor restarted it with a new pid; balance recovered from the Vault:
  alice     $60.00  #PID<0.150.0>
  bob       $65.00  #PID<0.149.0>
```

## Design notes

- A transfer is **not** atomic across both accounts: for a brief moment the money is "in flight". The test suite checks that the total is conserved once all concurrent transfers finish.
- The Vault is in-memory. If the whole application stops, balances are gone; see extensions.

## Possible extensions

- Persist snapshots to DETS, ETS with `:heir`, or Postgres via Ecto.
- Event sourcing: store the transaction log and rebuild the balance by replaying it.
- Idempotency keys so a retried transfer is never applied twice.
- Interest accrual with `Process.send_after/3` timers.
- Run accounts across a cluster with `:global` or Horde.
- A Phoenix LiveView dashboard showing live balances and pids.
