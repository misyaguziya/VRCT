import assert from "node:assert/strict";
import { test } from "node:test";
import { decodeOrdered, encodeOrdered, isRelayAllowed } from "./vrPanelWire.js";

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

test("the VR panel can ask for settings and the main features, but not for dangerous operations", () => {
    for (const path of ["/set/enable/translation", "/set/data/overlay_vr_panel_opacity", "/get/data/selected_tab_no", "/run/vr_panel_windows",
        "/run/swap_your_language_and_target_language", "/set/enable/ocr_capture"]) assert.equal(isRelayAllowed(path), true, path);
    for (const path of ["/run/shutdown", "/run/update_software", "/run/open_filepath_logs", "/run/open_filepath_config_file",
        "/run/download_whisper_weight", "/run/download_ctranslate2_weight", "/set/data/deepl_auth_key", "/set/data/websocket_auth_token",
        "relative/path", "", undefined, 3]) assert.equal(isRelayAllowed(path), false, String(path));
});
