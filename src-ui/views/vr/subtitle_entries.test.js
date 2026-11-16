import test from "node:test";
import assert from "node:assert/strict";
import { subtitleEntries, subtitleKey } from "./subtitle_entries.js";

const item = (message) => ({ message, transliteration: [] });
const log = (id, category, { status = "ok", source, translations = ["訳"] } = {}) => ({
    id, category, status, source, created_at: "12:00",
    messages: { original: item(`原文${id}`), translations: translations.map(item) },
});

test("pending and system logs are not subtitles", () => {
    const logs = [log(1, "sent", { status: "pending" }), log(2, "system"), log(3, "received")];
    assert.deepEqual(subtitleEntries(logs, "multi_line", false).map(e => e.id), [3]);
});

test("multiple lines show the last five sent and received", () => {
    const logs = [1, 2, 3, 4, 5, 6, 7].map(i => log(i, i % 2 ? "received" : "sent"));
    assert.deepEqual(subtitleEntries(logs, "multi_line", false).map(e => e.id), [3, 4, 5, 6, 7]);
});

test("one line shows the last received that is not from the chat bubbles", () => {
    const logs = [log(1, "received"), log(2, "received", { source: "ocr" }), log(3, "sent")];
    assert.deepEqual(subtitleEntries(logs, "single_line", false).map(e => e.id), [1]);
});

test("the original is small above the translations; without them it is large", () => {
    const [translated, untranslated] = subtitleEntries([log(1, "received"), log(2, "sent", { translations: [] })], "multi_line", false);
    assert.equal(translated.small.message, "原文1");
    assert.deepEqual(translated.large.map(i => i.message), ["訳"]);
    assert.equal(untranslated.small, null);
    assert.deepEqual(untranslated.large.map(i => i.message), ["原文2"]);
});

test("translations only: the original hidden, untranslated logs left out", () => {
    const entries = subtitleEntries([log(1, "received"), log(2, "received", { translations: [] })], "single_line", true);
    assert.deepEqual(entries.map(e => [e.id, e.small, e.large.map(i => i.message)]), [[1, null, ["訳"]]]);
});

test("the key changes with a new log, a translation arriving and the form", () => {
    const pending = [log(1, "received", { translations: [] })];
    const translated = [log(1, "received")];
    const keys = [
        subtitleKey("multi_line", subtitleEntries(pending, "multi_line", false)),
        subtitleKey("multi_line", subtitleEntries(translated, "multi_line", false)),
        subtitleKey("single_line", subtitleEntries(translated, "single_line", false)),
        subtitleKey("single_line", subtitleEntries([...translated, log(2, "received")], "single_line", false)),
    ];
    assert.equal(new Set(keys).size, keys.length);
    assert.equal(subtitleKey("multi_line", []), "multi_line:");
});
