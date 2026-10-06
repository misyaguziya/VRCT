import test from "node:test";
import assert from "node:assert/strict";
import { keepNewestVrLayout, tooltipMarker, tooltipGeometry } from "./vrPanelTooltip.js";

test("delayed GET/initialization snapshots cannot replace a newer session", () => {
    const current = { tooltip_epoch: 23, atlas: [1690, 880] };
    assert.equal(keepNewestVrLayout(current, { tooltip_epoch: 22 }), current);
    assert.equal(keepNewestVrLayout(current, { atlas: [1690, 880] }), current);
    const next = { tooltip_epoch: 24 };
    assert.equal(keepNewestVrLayout(current, next), next);
    const resize = { tooltip_epoch: 23, atlas: [2128, 1136] };
    assert.equal(keepNewestVrLayout(current, resize), resize);
});

test("48-bit epoch and 32-bit revision preserve every bit in Python marker order", () => {
    for (const [epoch, revision] of [[1, 1], [2 ** 47 + 12345, 2 ** 31 + 27], [2 ** 48 - 1, 2 ** 32 - 1]]) {
        const cells = tooltipMarker(epoch, revision);
        assert.equal(cells.length, 80);
        const packed = cells.reduce((value, bit) => value * 2n + BigInt(bit), 0n);
        assert.equal(packed, (BigInt(epoch) << 32n) | BigInt(revision));
    }
    assert.notDeepEqual(tooltipMarker(123, 4), tooltipMarker(123, 5));
    assert.notDeepEqual(tooltipMarker(123, 4), tooltipMarker(124, 4));
});

test("geometry stays in logical atlas pixels and clamps the arrow at both edges", () => {
    for (const scale of [0.5, 1, 1.25, 1.5, 2]) {
        // ランチャーは 952px 幅。左端の VRCT のマーク (60px) の右に、最初のボタン (x=84) が並ぶ
        const region = { left: 30, top: 70, width: 952 * scale, height: 128 * scale };
        const button = { left: 30 + 84 * scale, top: 70 + 12 * scale, width: 124 * scale, height: 104 * scale };
        assert.deepEqual(tooltipGeometry(region, button, 952, 128), { button: [84, 12, 124, 104], arrow_x: 134 });
        const right = { ...button, left: 30 + 840 * scale, width: 96 * scale };
        assert.deepEqual(tooltipGeometry(region, right, 952, 128), { button: [840, 12, 96, 104], arrow_x: 308 });
    }
    assert.equal(tooltipGeometry({ left: 0, top: 0, width: 0, height: 0 }, {}, 952, 128), null);
    assert.equal(tooltipGeometry({ left: 0, top: 0, width: 952, height: 128 },
        { left: -1, top: 12, width: 124, height: 104 }, 952, 128), null);
});
