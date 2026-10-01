import assert from "node:assert/strict";
import { test } from "node:test";
import { createLanguageMutationCoordinator } from "./languageMutationCoordinator.js";

const snapshot = { tab: "1", your: { 1: "Japanese" }, target: { 1: "English" }, selectedEngines: { 1: "CTranslate2" } };
const request = (requestId, source = "vr", endpoint = "/set/data/selected_target_languages") => ({ requestId, source, endpoint, expectedSnapshot: snapshot });
const setup = () => createLanguageMutationCoordinator(() => {});

test("push notifications and GETs cannot complete a language save", () => {
    const coordinator = setup();
    const write = request("vr-1");
    assert.equal(coordinator.begin(write, snapshot), true);
    for (const endpoint of ["/run/selected_target_languages", "/get/data/selected_target_languages"]) {
        assert.equal(coordinator.complete({ endpoint, status: 200 }), null);
        assert.equal(coordinator.getState().inFlight.requestId, "vr-1");
    }
    assert.equal(coordinator.complete({ endpoint: write.endpoint, status: 200 }).requestId, "vr-1");
    assert.equal(coordinator.getState().lastVrResult.kind, "success");
});

test("PC and VR writes are admitted one at a time; rejection retains the owner", () => {
    const coordinator = setup();
    assert.equal(coordinator.begin(request("pc-1", "pc"), snapshot), true);
    assert.equal(coordinator.begin(request("vr-2"), snapshot), false);
    assert.equal(coordinator.getState().inFlight.requestId, "pc-1");
    assert.equal(coordinator.getState().lastVrResult.requestId, "vr-2");
    coordinator.complete({ endpoint: request("pc-1").endpoint, status: 200 });
    assert.equal(coordinator.getState().lastVrResult.kind, "rejected");
});

test("stale preset or dictionaries cannot overwrite the main snapshot", () => {
    for (const field of Object.keys(snapshot)) {
        const coordinator = setup();
        const current = { ...snapshot, [field]: "changed on PC" };
        assert.equal(coordinator.begin(request("stale"), current), false);
        assert.equal(coordinator.getState().lastVrResult.reason, "stale");
        assert.equal(coordinator.getState().inFlight, null);
    }
});

test("final 400, 404, 423 and 500 release pending ownership as failures", () => {
    for (const status of [400, 404, 423, 500]) {
        const coordinator = setup();
        const write = request(String(status));
        coordinator.begin(write, snapshot);
        coordinator.complete({ endpoint: write.endpoint, status });
        assert.equal(coordinator.getState().inFlight, null);
        assert.equal(coordinator.getState().lastVrResult.kind, "failure");
        assert.equal(coordinator.getState().lastVrResult.status, status);
    }
});

test("timeout retains ownership, blocks retry, and attributes the late ACK to its original request", () => {
    const coordinator = setup();
    coordinator.begin(request("old"), snapshot);
    assert.equal(coordinator.markUnconfirmed("old", "timeout"), true);
    assert.equal(coordinator.begin(request("retry"), snapshot), false);
    assert.equal(coordinator.getState().inFlight.requestId, "old");
    coordinator.complete({ endpoint: request("old").endpoint, status: 200 });
    assert.equal(coordinator.getState().lastVrResult.requestId, "old");
    assert.equal(coordinator.getState().lastVrResult.kind, "success");
});

test("late write errors cannot replace an already received success", () => {
    const coordinator = setup();
    coordinator.begin(request("saved"), snapshot);
    coordinator.complete({ endpoint: request("saved").endpoint, status: 200 });
    assert.equal(coordinator.markUnconfirmed("saved", "write-unconfirmed"), false);
    assert.equal(coordinator.failBeforeSend("saved", "missing"), null);
    assert.equal(coordinator.getState().lastVrResult.kind, "success");
});

test("config rejection and backend restart do not falsely finish another request", () => {
    const coordinator = setup();
    coordinator.begin(request("first"), snapshot);
    coordinator.reject(request("locked"), "config-open");
    assert.equal(coordinator.getState().inFlight.requestId, "first");
    coordinator.reset();
    assert.equal(coordinator.getState().inFlight, null);
    assert.equal(coordinator.getState().lastVrResult.requestId, "first");
    assert.equal(coordinator.getState().lastVrResult.reason, "backend-restarted");
});

test("definitely unsent operations can release the guard", () => {
    const coordinator = setup();
    coordinator.begin(request("unsent"), snapshot);
    coordinator.failBeforeSend("unsent", "backend-unavailable");
    assert.equal(coordinator.getState().inFlight, null);
    assert.equal(coordinator.getState().lastVrResult.kind, "failure");
});
