import { strict as assert } from "node:assert";
import { describe, it } from "node:test";
import { run } from "../src/cli.js";
import { bitString, boundaryRuler } from "../src/render.js";

function capture(args: string[]): { code: number; out: string } {
  const chunks: string[] = [];
  const code = run(args, (s) => chunks.push(s));
  return { code, out: chunks.join("\n") };
}

describe("render", () => {
  it("bitString groups octets", () => {
    assert.equal(bitString(0xc0a80a4d, 26), "11000000.10101000.00001010.01001101");
  });
  it("ruler marks network vs host bits", () => {
    assert.equal(boundaryRuler(26), "nnnnnnnn.nnnnnnnn.nnnnnnnn.nnhhhhhh");
    assert.equal(boundaryRuler(0), "hhhhhhhh.hhhhhhhh.hhhhhhhh.hhhhhhhh");
  });
});

describe("cli", () => {
  it("describes a subnet", () => {
    const { code, out } = capture(["192.168.10.77/26"]);
    assert.equal(code, 0);
    assert.match(out, /Broadcast\s+192\.168\.10\.127/);
    assert.match(out, /Usable hosts\s+62/);
    assert.match(out, /26 network bits, 6 host bits/);
    assert.ok(!out.includes("\x1b["), "plain output has no ANSI codes");
  });
  it("accepts a dotted mask as a second argument", () => {
    assert.match(capture(["10.1.2.3", "255.255.255.0"]).out, /Subnet 10\.1\.2\.0\/24/);
  });
  it("emits JSON", () => {
    const parsed = JSON.parse(capture(["10.0.0.1/8", "--json"]).out);
    assert.equal(parsed.cidr, "10.0.0.0/8");
    assert.equal(parsed.usableHosts, 16777214);
  });
  it("split / vlsm / summarize / contains", () => {
    assert.match(capture(["split", "10.0.0.0/24", "/26"]).out, /4 × \/26[\s\S]*10\.0\.0\.192\/26/);
    assert.match(capture(["vlsm", "10.0.0.0/24", "lan:100", "p2p:2"]).out, /lan\s+100\s+10\.0\.0\.0\/25/);
    assert.equal(capture(["summarize", "10.0.0.0/25", "10.0.0.128/25"]).out, "10.0.0.0/24");
    assert.equal(capture(["contains", "10.0.0.0/8", "10.9.9.9"]).code, 0);
    assert.equal(capture(["contains", "10.0.0.0/8", "11.0.0.0"]).code, 2);
  });
  it("reports errors with a nonzero exit code", () => {
    const { code, out } = capture(["300.1.1.1/24"]);
    assert.equal(code, 1);
    assert.match(out, /^error:/);
    assert.equal(capture([]).code, 1);
    assert.equal(capture(["--help"]).code, 0);
  });
});
