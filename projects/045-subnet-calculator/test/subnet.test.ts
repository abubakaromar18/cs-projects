import { strict as assert } from "node:assert";
import { describe as group, it } from "node:test";
import { ParseError, formatIp, parseIp } from "../src/ipv4.js";
import { Subnet, describe, prefixForHosts, summarize, vlsm } from "../src/subnet.js";

const cidrs = (list: Subnet[]) => list.map(String);

group("Subnet.parse", () => {
  it("accepts CIDR, mask and bare forms, masking host bits", () => {
    assert.equal(String(Subnet.parse("192.168.10.77/26")), "192.168.10.64/26");
    assert.equal(String(Subnet.parse("10.1.2.3 255.255.0.0")), "10.1.0.0/16");
    assert.equal(String(Subnet.parse("10.1.2.3/255.0.0.0")), "10.0.0.0/8");
    assert.equal(String(Subnet.parse("8.8.8.8")), "8.8.8.8/32");
  });
  it("rejects garbage", () => {
    for (const bad of ["10.0.0.0/33", "10.0.0.0/x", "10.0.0.0/24/1", "nope/24", "10.0.0.0/255.0.255.0"]) {
      assert.throws(() => Subnet.parse(bad), ParseError, bad);
    }
  });
});

group("derived properties", () => {
  it("/26", () => {
    const s = Subnet.parse("192.168.10.77/26");
    assert.equal(formatIp(s.mask), "255.255.255.192");
    assert.equal(formatIp(s.wildcard), "0.0.0.63");
    assert.equal(formatIp(s.broadcast), "192.168.10.127");
    assert.equal(formatIp(s.firstHost), "192.168.10.65");
    assert.equal(formatIp(s.lastHost), "192.168.10.126");
    assert.equal(s.size, 64);
    assert.equal(s.usableHosts, 62);
  });
  it("/31 and /32 use every address (RFC 3021)", () => {
    const p2p = Subnet.parse("10.0.0.0/31");
    assert.equal(p2p.usableHosts, 2);
    assert.equal(formatIp(p2p.firstHost), "10.0.0.0");
    assert.equal(formatIp(p2p.lastHost), "10.0.0.1");
    assert.equal(Subnet.parse("10.0.0.9/32").usableHosts, 1);
  });
  it("/0 covers the whole space", () => {
    const all = Subnet.parse("1.2.3.4/0");
    assert.equal(all.size, 2 ** 32);
    assert.equal(formatIp(all.broadcast), "255.255.255.255");
    assert.equal(all.usableHosts, 2 ** 32 - 2);
  });
  it("high addresses stay unsigned", () => {
    const s = Subnet.parse("200.1.1.1/8");
    assert.ok(s.network > 0);
    assert.equal(formatIp(s.broadcast), "200.255.255.255");
  });
});

group("membership", () => {
  const net = Subnet.parse("172.16.0.0/12");
  it("contains", () => {
    assert.ok(net.contains(parseIp("172.31.255.255")));
    assert.ok(!net.contains(parseIp("172.32.0.0")));
  });
  it("covers / overlaps", () => {
    assert.ok(net.covers(Subnet.parse("172.20.0.0/16")));
    assert.ok(!Subnet.parse("172.20.0.0/16").covers(net));
    assert.ok(Subnet.parse("172.20.0.0/16").overlaps(net));
    assert.ok(!net.overlaps(Subnet.parse("192.168.0.0/16")));
  });
});

group("split", () => {
  it("splits evenly", () => {
    assert.deepEqual(cidrs(Subnet.parse("10.0.0.0/24").split(26)), [
      "10.0.0.0/26", "10.0.0.64/26", "10.0.0.128/26", "10.0.0.192/26",
    ]);
  });
  it("same prefix yields itself; larger prefix is rejected", () => {
    assert.deepEqual(cidrs(Subnet.parse("10.0.0.0/24").split(24)), ["10.0.0.0/24"]);
    assert.throws(() => Subnet.parse("10.0.0.0/24").split(16), ParseError);
    assert.throws(() => Subnet.parse("0.0.0.0/0").split(24), ParseError);
  });
});

group("prefixForHosts", () => {
  it("picks the smallest fitting block", () => {
    assert.equal(prefixForHosts(1), 32);
    assert.equal(prefixForHosts(2), 31);
    assert.equal(prefixForHosts(3), 29);
    assert.equal(prefixForHosts(62), 26);
    assert.equal(prefixForHosts(63), 25);
    assert.equal(prefixForHosts(254), 24);
    assert.equal(prefixForHosts(255), 23);
  });
  it("rejects nonsense", () => {
    assert.throws(() => prefixForHosts(0), ParseError);
    assert.throws(() => prefixForHosts(2 ** 32), ParseError);
  });
});

group("vlsm", () => {
  it("allocates largest first, aligned and non-overlapping", () => {
    const parent = Subnet.parse("192.168.0.0/24");
    const plan = vlsm(parent, [
      { name: "p2p", hosts: 2 },
      { name: "lan", hosts: 100 },
      { name: "wifi", hosts: 50 },
      { name: "mgmt", hosts: 10 },
    ]);
    assert.deepEqual(plan.map((a) => `${a.name}=${a.subnet}`), [
      "lan=192.168.0.0/25", "wifi=192.168.0.128/26", "mgmt=192.168.0.192/28", "p2p=192.168.0.208/31",
    ]);
    for (const a of plan) {
      assert.ok(parent.covers(a.subnet));
      assert.ok(a.subnet.usableHosts >= a.hosts);
      for (const b of plan) if (a !== b) assert.ok(!a.subnet.overlaps(b.subnet));
    }
  });
  it("fails when space runs out", () => {
    const parent = Subnet.parse("10.0.0.0/26");
    assert.throws(() => vlsm(parent, [{ name: "a", hosts: 30 }, { name: "b", hosts: 30 }, { name: "c", hosts: 2 }]), /no room/);
    assert.throws(() => vlsm(parent, [{ name: "big", hosts: 100 }]), /larger than/);
  });
});

group("summarize", () => {
  it("merges adjacent siblings into a supernet", () => {
    const input = ["10.0.0.0/24", "10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"].map((c) => Subnet.parse(c));
    assert.deepEqual(cidrs(summarize(input)), ["10.0.0.0/22"]);
  });
  it("drops covered blocks and handles unaligned runs", () => {
    const input = ["10.0.1.0/24", "10.0.2.0/24", "10.0.2.128/25", "10.0.3.0/24"].map((c) => Subnet.parse(c));
    assert.deepEqual(cidrs(summarize(input)), ["10.0.1.0/24", "10.0.2.0/23"]);
  });
  it("keeps disjoint blocks separate and sorted", () => {
    const input = ["192.168.1.0/24", "10.0.0.0/8"].map((c) => Subnet.parse(c));
    assert.deepEqual(cidrs(summarize(input)), ["10.0.0.0/8", "192.168.1.0/24"]);
  });
  it("aggregates up to the whole address space", () => {
    assert.deepEqual(cidrs(summarize([Subnet.parse("0.0.0.0/1"), Subnet.parse("128.0.0.0/1")])), ["0.0.0.0/0"]);
  });
  it("preserves exactly the same address count (randomised)", () => {
    let seed = 42;
    const rand = () => ((seed = (Math.imul(seed, 1103515245) + 12345) >>> 0) / 2 ** 32);
    for (let trial = 0; trial < 50; trial++) {
      const input = Array.from({ length: 8 }, () =>
        new Subnet(parseIp("10.0.0.0") + Math.floor(rand() * 4096), 24 + Math.floor(rand() * 9)));
      const covered = new Set<number>();
      for (const s of input) for (let ip = s.network; ip <= s.broadcast; ip++) covered.add(ip);
      const out = summarize(input);
      const total = out.reduce((n, s) => n + s.size, 0);
      assert.equal(total, covered.size);
      for (const s of out) for (let ip = s.network; ip <= s.broadcast; ip++) assert.ok(covered.has(ip));
    }
  });
});

group("describe", () => {
  it("builds a full report", () => {
    const r = describe("172.20.5.9/20");
    assert.equal(r.address, "172.20.5.9");
    assert.equal(r.cidr, "172.20.0.0/20");
    assert.equal(r.netmask, "255.255.240.0");
    assert.equal(r.broadcast, "172.20.15.255");
    assert.equal(r.usableHosts, 4094);
    assert.equal(r.addressClass, "B");
    assert.match(r.scope, /RFC 1918/);
  });
});
