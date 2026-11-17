import test from "node:test";
import assert from "node:assert/strict";
import { SUBTITLE_FONT_SIZE, nextShownSince, subtitleEntries, subtitleKey, subtitleSmallFontSize } from "./subtitle_entries.js";

test("the original's size is about two thirds of the translation's (as before by default)", () => {
    assert.equal(subtitleSmallFontSize(27), 18);
    assert.equal(subtitleSmallFontSize(28), 19);
    assert.equal(subtitleSmallFontSize(SUBTITLE_FONT_SIZE.min), 11);
    assert.equal(subtitleSmallFontSize(SUBTITLE_FONT_SIZE.max), 37);
});

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
});

test("a sent message translated after a later received one changes the key", () => {
    const sent_pending = log(1, "sent", { status: "pending" });
    const received = log(2, "received");
    const before = subtitleKey("multi_line", subtitleEntries([sent_pending, received], "multi_line", false));
    const after = subtitleKey("multi_line", subtitleEntries([log(1, "sent"), received], "multi_line", false));
    assert.notEqual(before, after);
});

test("after_id: only the logs after it (the one-line subtitle shows what came after it was shown)", () => {
    const logs = [log(1, "received"), log(2, "sent"), log(3, "received")];
    assert.deepEqual(subtitleEntries(logs.slice(0, 2), "single_line", false, 2).map(e => e.id), []);
    assert.deepEqual(subtitleEntries(logs, "single_line", false, 2).map(e => e.id), [3]);
    // an id no longer in the logs: all of them
    assert.deepEqual(subtitleEntries(logs, "single_line", false, 99).map(e => e.id), [3]);
    assert.deepEqual(subtitleEntries(logs, "multi_line", false).map(e => e.id), [1, 2, 3]);
});

test("the one-line subtitle counts again from a form change or the log window opened, not while it stays", () => {
    let s = nextShownSince(null, "single_line", true, "a");
    assert.equal(s.after_id, "a");
    s = nextShownSince(s, "single_line", true, "b");
    assert.equal(s.after_id, "a");
    s = nextShownSince(s, "single_line", false, "c");
    assert.equal(s.after_id, "a");
    s = nextShownSince(s, "single_line", true, "d");
    assert.equal(s.after_id, "d");
    s = nextShownSince(s, "multi_line", true, "e");
    assert.equal(s.after_id, null);
    s = nextShownSince(s, "single_line", true, "f");
    assert.equal(s.after_id, "f");
});

test("nothing to show: still a key of its own per form (told at once on a form change)", () => {
    const empty = [subtitleKey("multi_line", []), subtitleKey("single_line", subtitleEntries([log(1, "sent")], "single_line", false))];
    assert.ok(empty.every(key => typeof key === "string"));
    assert.notEqual(empty[0], empty[1]);
    assert.notEqual(empty[1], subtitleKey("single_line", subtitleEntries([log(1, "received")], "single_line", false)));
});
