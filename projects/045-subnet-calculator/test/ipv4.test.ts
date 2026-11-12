import { strict as assert } from "node:assert";
import { describe, it } from "node:test";
import {
  ParseError,
  addressClass,
  addressScope,
  formatIp,
  maskToPrefix,
  parseIp,
  popcount,
  prefixToMask,
  toBinary,
} from "../src/ipv4.js";

describe("parseIp / formatIp", () => {
  it("round-trips addresses including the top bit", () => {
    for (const ip of ["0.0.0.0", "10.1.2.3", "192.168.0.1", "255.255.255.255", "128.0.0.0"]) {
      assert.equal(formatIp(parseIp(ip)), ip);
    }
    assert.equal(parseIp("255.255.255.255"), 0xffffffff);
    assert.equal(parseIp("192.168.1.1"), 0xc0a80101);
  });

  it("rejects malformed input", () => {
    for (const bad of ["", "1.2.3", "1.2.3.4.5", "256.0.0.1", "1.2.3.-4", "01.2.3.4", "a.b.c.d", "1..2.3"]) {
      assert.throws(() => parseIp(bad), ParseError, bad);
    }
  });
});

describe("masks", () => {
  it("converts prefix to mask at the edges", () => {
    assert.equal(prefixToMask(0), 0);
    assert.equal(formatIp(prefixToMask(24)), "255.255.255.0");
    assert.equal(formatIp(prefixToMask(19)), "255.255.224.0");
    assert.equal(prefixToMask(32), 0xffffffff);
  });

  it("round-trips every prefix", () => {
    for (let p = 0; p <= 32; p++) assert.equal(maskToPrefix(prefixToMask(p)), p);
  });

  it("rejects non-contiguous masks and bad prefixes", () => {
    assert.throws(() => maskToPrefix(parseIp("255.0.255.0")), ParseError);
    assert.throws(() => prefixToMask(33), ParseError);
    assert.throws(() => prefixToMask(-1), ParseError);
    assert.throws(() => prefixToMask(1.5), ParseError);
  });
});

describe("bit helpers", () => {
  it("popcount", () => {
    assert.equal(popcount(0), 0);
    assert.equal(popcount(0xffffffff), 32);
    assert.equal(popcount(0x80000001), 2);
  });
  it("toBinary pads to 32 bits", () => {
    assert.equal(toBinary(1), "0".repeat(31) + "1");
    assert.equal(toBinary(0xffffffff), "1".repeat(32));
  });
});

describe("classification", () => {
  it("classful", () => {
    assert.equal(addressClass(parseIp("10.0.0.1")), "A");
    assert.equal(addressClass(parseIp("172.16.0.1")), "B");
    assert.equal(addressClass(parseIp("192.168.0.1")), "C");
    assert.equal(addressClass(parseIp("224.0.0.5")), "D");
    assert.equal(addressClass(parseIp("250.0.0.1")), "E");
  });
  it("special-purpose scopes", () => {
    assert.match(addressScope(parseIp("10.20.30.40")), /Private/);
    assert.match(addressScope(parseIp("172.31.255.255")), /Private/);
    assert.equal(addressScope(parseIp("172.32.0.0")), "Public");
    assert.match(addressScope(parseIp("127.0.0.1")), /Loopback/);
    assert.match(addressScope(parseIp("100.100.0.1")), /Carrier-grade/);
    assert.match(addressScope(parseIp("255.255.255.255")), /broadcast/);
    assert.equal(addressScope(parseIp("8.8.8.8")), "Public");
  });
});
