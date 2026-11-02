# 026 · Chat over TCP

A multi-client chat server and terminal client in Go, using only the standard
library. Many users connect over raw TCP, pick nicknames, chat in a shared
room, send private messages and emotes. The server shuts down cleanly on Ctrl-C.

## Key CS concepts

- **TCP sockets.** `net.Listen`, `Accept` and `Dial`, with a newline-delimited
  framing protocol layered on top of the byte stream.
- **The hub pattern (CSP).** One goroutine owns all shared state (the set of
  clients and their nicknames). Other goroutines only send it events over a
  channel, so the room needs no mutexes.
- **Reader/writer goroutines per connection.** Reads and writes for a socket
  never block each other, and only one goroutine ever writes to a given
  connection.
- **Backpressure.** Each client has a bounded outbox. If a slow client lets it
  fill up, the server disconnects that client instead of stalling the room.
- **Graceful shutdown.** Cancelling a `context.Context` closes the listener and
  expires read deadlines. Every client gets a goodbye line before the server
  waits on a `sync.WaitGroup` for all goroutines to exit.
- **Protocol parsing and validation.** Commands are parsed into a typed struct,
  with clear errors for bad input. Line length is bounded to resist abuse.

## Layout

```
cmd/chat-server/     server entry point (flags, signal handling)
cmd/chat-client/     terminal client: stdin → socket, socket → stdout
internal/protocol/   line protocol: command parsing, nickname validation
internal/server/     hub, connection handling, broadcast, shutdown
```

## Build, run, test

Requires Go 1.22+.

```sh
make server                 # listens on 127.0.0.1:9000
make client                 # in another terminal (repeat for more users)
go run ./cmd/chat-client -nick alice

make test                   # go test -race ./...
make build                  # binaries in ./bin
```

Any line-based TCP tool also works as a client, e.g. `nc 127.0.0.1 9000`.
The server binds to localhost by default. Pass `-addr :9000` to accept
connections from your own LAN.

### Commands

| Command              | Effect                          |
|----------------------|---------------------------------|
| `text`               | broadcast to everyone else      |
| `/nick <name>`       | change nickname (unique, case-insensitive) |
| `/msg <name> <text>` | private message                 |
| `/me <action>`       | emote: `* alice waves`          |
| `/who`               | list online users               |
| `/help`              | list commands                   |
| `/quit`              | disconnect                      |

## Example session

Alice's terminal:

```
*** welcome, you are guest1 (1 online). Type /help for commands.
*** guest1 is now known as alice
*** guest2 joined
*** guest2 is now known as bob
*** online (2): alice, bob
[pm from bob] hey
*** bye
```

Bob's terminal:

```
*** welcome, you are guest2 (2 online). Type /help for commands.
*** guest2 is now known as bob
<alice> hi bob
[pm to alice] hey
*** alice left
```

## Tests

- `internal/protocol`: table-driven tests for every command, edge case and
  nickname rule.
- `internal/server`: integration tests that start a real server on a random
  localhost port and connect real TCP clients. They cover broadcast, private
  messages, nickname conflicts, `/quit` vs. abrupt disconnects, 20 concurrent
  clients and graceful shutdown. All tests run under the race detector.

## Possible extensions

- Multiple rooms/channels (`/join #go`) with per-room hubs
- TLS with `crypto/tls` and a self-signed certificate
- Message history replay for newly joined users
- Rate limiting per client (token bucket)
- A JSON wire format, or a WebSocket gateway for browser clients
- Persistent accounts with password authentication
