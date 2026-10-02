import assert from "node:assert/strict";
import { test } from "node:test";
import { decodeOrdered, encodeOrdered } from "./vrPanelWire.js";

// Tauri の emit を通ったときの変化を模す: キーを辞書順にし、undefined を落とし、NaN を null にする
const sortKeysDeep = value => Array.isArray(value) ? value.map(sortKeysDeep)
    : value && typeof value === "object" ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sortKeysDeep(value[key])])) : value;
const emitRoundTrip = value => JSON.parse(JSON.stringify(sortKeysDeep(value)));

test("object key order survives the emit round trip", () => {
    const fonts = { "Yu Gothic UI": "Yu Gothic UI", arial: "arial", Arial: "Arial", "メイリオ": "メイリオ" };
    const plain = emitRoundTrip(fonts);
    assert.notDeepEqual(Object.keys(plain), Object.keys(fonts)); // 素のままでは並びが変わる
    assert.deepEqual(Object.keys(decodeOrdered(emitRoundTrip(encodeOrdered(fonts)))), Object.keys(fonts));
});

test("nested atoms, arrays and primitives are restored unchanged", () => {
    const atom = { state: "ok", data: { devices: { b: "b", a: "a" }, list: [{ z: 1, a: [{ y: 2, x: null }] }, "text", 3, true, null] } };
    assert.deepEqual(decodeOrdered(emitRoundTrip(encodeOrdered(atom))), atom);
    assert.deepEqual(Object.keys(decodeOrdered(emitRoundTrip(encodeOrdered(atom))).data.devices), ["b", "a"]);
    assert.deepEqual(decodeOrdered(emitRoundTrip(encodeOrdered([1, "a"]))), [1, "a"]);
});

test("a value that was not encoded passes through", () => {
    assert.deepEqual(decodeOrdered({ a: 1 }), { a: 1 });
});
