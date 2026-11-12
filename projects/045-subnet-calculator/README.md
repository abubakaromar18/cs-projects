# 045 · Subnet Calculator

A dependency-free IPv4 CIDR calculator for the command line, written in TypeScript. Give it an address and a prefix and it prints the netmask, network, broadcast, host range and address scope. It also shows the 32 bits with the network part and the host part marked, so you can see where the boundary falls. It can also split a block into equal subnets, build a VLSM plan, and summarize a list of routes into the fewest CIDR blocks.

## Key CS concepts

- **Addresses as 32-bit integers.** An IPv4 address is just a `uint32`. Every operation here is bitwise math. JavaScript's bitwise operators are *signed* 32-bit, so results are normalized with `>>> 0`. The `<< 32` edge case (a no-op in JS) gets special handling for `/0`.
- **Masks and wildcards.** `mask = ~0 << (32 - p)`, `network = ip & mask`, `broadcast = network | ~mask`. A mask is valid only if `~mask + 1` is a power of two: `(inv & (inv + 1)) === 0`.
- **Popcount (Hamming weight).** A SWAR bit-counting trick converts a mask back to its prefix length.
- **Alignment.** A `/p` block must start on a multiple of `2^(32-p)`. VLSM sorts requests largest-first, which keeps every block aligned and lets a simple bump allocator do the job.
- **Interval merging + greedy cover.** Route summarization sorts and merges address intervals. It then covers each interval with the largest aligned block that fits, using trailing zeros (`Math.clz32(x & -x)`) to find the alignment.
- **Special cases from the RFCs.** `/31` point-to-point links (RFC 3021), `/32` host routes, and the RFC 1918, RFC 6598 and RFC 5737 special-purpose ranges.

## Project layout

```
src/ipv4.ts     parsing, formatting, mask math, popcount, address class & scope
src/subnet.ts   Subnet class, split, VLSM allocator, route summarization
src/render.ts   text tables and the bit-level breakdown (optional ANSI color)
src/cli.ts      argument handling; `run()` is pure so it can be tested
test/*.test.ts  node:test suites (36 tests, including a randomized property test)
```

## Build, run, test

Requires Node.js 18+.

```bash
npm install
npm test                                 # compiles with tsc and runs node --test
npm run build
node dist/cli.js 192.168.10.77/26
npm link && subnet 10.0.0.1 255.255.0.0  # optional: install the `subnet` command
```

Commands:

```
subnet <ip>[/prefix | mask]           Describe a subnet
subnet split <cidr> <newPrefix>       Split into equal subnets
subnet vlsm <cidr> <name:hosts>...    VLSM plan
subnet summarize <cidr>...            Aggregate routes into minimal CIDR set
subnet contains <cidr> <ip>           Exit 0 if inside, 2 if not
  --json  --no-color
```

## Example output

```
$ subnet 192.168.10.77/26
Subnet 192.168.10.64/26

  Address           192.168.10.77
  Netmask           255.255.255.192 = /26
  Wildcard          0.0.0.63
  Network           192.168.10.64
  Broadcast         192.168.10.127
  Host range        192.168.10.65 – 192.168.10.126
  Total addresses   64
  Usable hosts      62
  Class / scope     C · Private (RFC 1918)

Bit breakdown  (26 network bits, 6 host bits)

                    nnnnnnnn.nnnnnnnn.nnnnnnnn.nnhhhhhh
  Address           11000000.10101000.00001010.01001101
  Netmask           11111111.11111111.11111111.11000000
  Network           11000000.10101000.00001010.01000000
  Broadcast         11000000.10101000.00001010.01111111
```

In a terminal, network bits are shown in cyan and host bits in yellow.

```
$ subnet vlsm 192.168.0.0/24 lan:100 wifi:50 mgmt:10 p2p:2
VLSM plan for 192.168.0.0/24

  Name             Need  Subnet               Usable  Host range
  lan               100  192.168.0.0/25          126  192.168.0.1 – 192.168.0.126
  wifi               50  192.168.0.128/26         62  192.168.0.129 – 192.168.0.190
  mgmt               10  192.168.0.192/28         14  192.168.0.193 – 192.168.0.206
  p2p                 2  192.168.0.208/31          2  192.168.0.208 – 192.168.0.209

  210 of 256 addresses allocated (82.0%)

$ subnet summarize 10.0.0.0/24 10.0.1.0/24 10.0.2.0/24 10.0.3.0/24
10.0.0.0/22
```

## Possible extensions

- IPv6 support using `bigint` (128-bit math, `::` compression).
- A browser UI with a clickable bit grid that lets you drag the prefix boundary.
- Subtraction: exclude a block from a range (as in `aws ec2` CIDR planning).
- Read a route table from a file and report overlapping or shadowed routes.
- A VLSM mode that minimizes fragmentation when existing allocations are fixed.
