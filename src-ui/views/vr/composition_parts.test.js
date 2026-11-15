import test from "node:test";
import assert from "node:assert/strict";
import { compositionParts } from "./composition_parts.js";

const styles = { preedit: "preedit", selection: "selection", selected: "selected", over: "over" };
const sides = parts => [false, true].map(after => parts.filter(p => !!p.after === after).map(p => p.text).join(""));

test("preedit caret moves independently of candidate selection and committed suffix", () => {
    for (let cursor = 0; cursor <= 5; cursor++) {
        const parts = compositionParts({ text: "前", after: "後", composition: { preedit: "今日はいい", selection: [2, 4], cursor } }, styles);
        assert.deepEqual(sides(parts), ["前" + "今日はいい".slice(0, cursor), "今日はいい".slice(cursor) + "後"]);
        assert.equal(parts.filter(p => p.className === "selection").map(p => p.text).join(""), "はい");
    }
});

test("legacy composition without cursor stays at its end", () => {
    assert.deepEqual(sides(compositionParts({ text: "", after: "後", composition: { preedit: "かな", selection: [0, 2] } }, styles)), ["かな", "後"]);
});

test("emoji and 144-character overflow retain their order across the caret", () => {
    const parts = compositionParts({ text: "a".repeat(142), after: "後", composition: { preedit: "😀かな", selection: [0, 3], cursor: 1 } }, styles);
    assert.deepEqual(sides(parts), ["a".repeat(142) + "😀", "かな後"]);
    assert.equal(parts.filter(p => p.className?.includes("over")).map(p => p.text).join(""), "な後");
});

test("committed text selection and Korean syllable keep their caret behavior", () => {
    const parts = compositionParts({ text: "前字", after: "後字", selected: [1, 1], syllable: "한" }, styles);
    assert.deepEqual(sides(parts), ["前字한", "後字"]);
    assert.equal(parts.filter(p => p.className === "selected").map(p => p.text).join(""), "字後");
});
