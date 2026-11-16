import test from "node:test";
import assert from "node:assert/strict";
import { isInteractionCancel } from "./interaction.js";

test("ordered native cancellation survives DPI scaling", () => {
    for (const scale of [1, 1.5, 2, 3, 4]) {
        assert.equal(isInteractionCancel({ clientX: -30000 / scale, clientY: -30000 / scale }), true);
    }
});

test("normal release and ordinary outside release remain releases", () => {
    for (const [clientX, clientY] of [[10, 20], [-1, -1], [-100, 50], [100, -100]]) {
        assert.equal(isInteractionCancel({ clientX, clientY }), false);
    }
});
