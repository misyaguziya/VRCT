import { test } from "node:test";
import assert from "node:assert/strict";
import { configPageAfterVrPanelGone, isUntouchedVrWindows, rememberedVrWindows, restoreVrWindows, vrPanelWindowWanted } from "./vrPanelWindows.js";

test("the VR view's window: made once SteamVR connects, kept while it is gone, dropped when the VR UI goes off", () => {
    let has = false;
    has = vrPanelWindowWanted(has, true, false);
    assert.equal(has, false, "the VR UI on without SteamVR: no window");
    has = vrPanelWindowWanted(has, true, true);
    assert.equal(has, true);
    has = vrPanelWindowWanted(has, true, false);
    assert.equal(has, true, "SteamVR gone: kept (not made again)");
    has = vrPanelWindowWanted(has, false, false);
    assert.equal(has, false);
    has = vrPanelWindowWanted(has, true, false);
    assert.equal(has, false, "on again without SteamVR: none until it connects");
});

test("only the log window and the keyboard are remembered (not the popups)", () => {
    assert.deepEqual(rememberedVrWindows({ log: true, popup: true, keyboard: false }), { log: true, keyboard: false });
    assert.deepEqual(rememberedVrWindows(null), { log: false, keyboard: false });
});

test("a VR view made again opens what was open, and closes nothing", () => {
    const fresh = { log: false, popup: null, keyboard: false };
    assert.deepEqual(restoreVrWindows(fresh, { log: true, keyboard: true }), { log: true, popup: null, keyboard: true });
    // the subtitle form opened the log already: kept
    assert.deepEqual(restoreVrWindows({ ...fresh, log: true }, { log: false, keyboard: false }), { ...fresh, log: true });
});

test("the untouched first state is not reported (it would overwrite what is remembered)", () => {
    assert.equal(isUntouchedVrWindows({ log: false, popup: null, keyboard: false }), true);
    assert.equal(isUntouchedVrWindows({ log: false, popup: "language", keyboard: false }), false);
    assert.equal(isUntouchedVrWindows({ log: true, popup: null, keyboard: false }), false);
});

test("the VR view gone: a settings page it opened is closed, one the desktop opened is left", () => {
    assert.equal(configPageAfterVrPanelGone(true), false);
    assert.equal(configPageAfterVrPanelGone(false), null);
});
