import test from "node:test";
import assert from "node:assert/strict";
import { createKeyRepeat } from "./key_repeat.js";

const setup = (t) => {
    t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const repeat = createKeyRepeat();
    t.after(repeat.stop);
    return repeat;
};

test("hold sends one immediate key, then repeats at the existing 580/660ms timing", (t) => {
    const repeat = setup(t);
    let calls = 0;
    repeat.start(() => calls++);
    assert.equal(calls, 1);
    t.mock.timers.tick(500);
    t.mock.timers.tick(79);
    assert.equal(calls, 1);
    t.mock.timers.tick(1);
    assert.equal(calls, 2);
    t.mock.timers.tick(80);
    assert.equal(calls, 3);
});

for (const elapsed of [100, 500, 580, 820]) {
    test(`stop at ${elapsed}ms prevents all subsequent keys`, (t) => {
        const repeat = setup(t);
        let calls = 0;
        repeat.start(() => calls++);
        // Advance across the timeout boundary separately so interval time is exact.
        t.mock.timers.tick(Math.min(elapsed, 500));
        if (elapsed > 500) t.mock.timers.tick(elapsed - 500);
        repeat.stop();
        const stopped = calls;
        repeat.stop(); // Repeated leave/release/cleanup must be harmless.
        t.mock.timers.tick(5000);
        assert.equal(calls, stopped);
    });
}

test("a new held key replaces the previous repeat without overlapping timers", (t) => {
    const repeat = setup(t);
    let backspaces = 0;
    let arrows = 0;
    repeat.start(() => backspaces++);
    t.mock.timers.tick(500);
    t.mock.timers.tick(80);
    assert.equal(backspaces, 2);
    repeat.start(() => arrows++);
    assert.equal(arrows, 1);
    t.mock.timers.tick(500);
    t.mock.timers.tick(80);
    assert.equal(backspaces, 2);
    assert.equal(arrows, 2);
});
