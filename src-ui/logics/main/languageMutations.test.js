import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const moduleUrl = code => `data:text/javascript;base64,${Buffer.from(code).toString("base64")}`;
const atomNames = ["LanguageMutation", "NotificationStatus", "SelectedPresetTabNumber", "SelectedYourLanguages",
    "SelectedTargetLanguages", "SelectedTranslationEngines", "TranslationEngines"];
const getters = ["selected_tab_no", "selected_your_languages", "selected_target_languages", "selected_translation_engines", "selectable_translation_engines"];
const fields = ["SelectedPresetTabNumber", "SelectedYourLanguages", "SelectedTargetLanguages", "SelectedTranslationEngines", "TranslationEngines"];

async function setup() {
    // Load the actual adapter with only its storage / translation dependencies
    // replaced. This keeps the tests independent of Vite aliases and React.
    const storageUrl = moduleUrl(`
        export const history = [];
        export const values = {};
        export const getDefaultStore = () => ({
            get: name => values[name],
            set: (name, value) => {
                values[name] = typeof value === "function" ? value(values[name]) : value;
                history.push({name, value:structuredClone(values[name])});
            },
        });
    `) + `#${crypto.randomUUID()}`;
    const storage = await import(storageUrl);
    for (const name of atomNames) storage.values[name] = { state: "ok", data: {} };
    storage.values.SelectedPresetTabNumber.data = "1";
    storage.values.LanguageMutation.data = { inFlight: null, lastVrResult: null, isResyncing: false };
    const atomsUrl = moduleUrl(atomNames.map(name => `export const Atom_${name} = "${name}";`).join("\n"));
    const translationUrl = moduleUrl("export default {t: key => key};");
    const coordinatorUrl = new URL("./languageMutationCoordinator.js", import.meta.url).href;
    const source = (await readFile(new URL("./languageMutations.js", import.meta.url), "utf8"))
        .replace('"jotai"', JSON.stringify(storageUrl))
        .replace('"@store"', JSON.stringify(atomsUrl))
        .replace('"i18next"', JSON.stringify(translationUrl))
        .replace('"./languageMutationCoordinator"', JSON.stringify(coordinatorUrl));
    const adapter = await import(moduleUrl(source));
    const request = (id = "first", source = "vr") => ({ requestId: id, source,
        endpoint: "/set/data/selected_target_languages", expectedSnapshot: adapter.getLanguageSnapshot() });
    const calls = [];
    const send = async endpoint => { calls.push(endpoint); return true; };
    return { adapter, ...storage, request, calls, send };
}

test("early push does not release the shared write guard", async () => {
    const {adapter,values,request} = await setup();
    try {
        const write = request();
        assert.equal(adapter.beginLanguageMutation(write), true);
        values.SelectedTargetLanguages = {state:"ok",data:{changed:"push"}};
        assert.equal(adapter.canChangeLanguageSettings(), false);
        adapter.receiveLanguageMutation({endpoint:write.endpoint,status:200},async () => true);
        assert.equal(adapter.canChangeLanguageSettings(), true);
    } finally {adapter.resetLanguageMutations();}
});

test("failure publishes resync ownership before its result and retains it until all five GETs", async () => {
    const {adapter,values,history,request,calls,send} = await setup();
    try {
        const write = request();adapter.beginLanguageMutation(write);
        adapter.receiveLanguageMutation({endpoint:write.endpoint,status:500},send);
        assert.equal(calls.length,5);
        const failure = history.find(item => item.name === "LanguageMutation" && item.value.data.lastVrResult?.kind === "failure");
        assert.equal(failure.value.data.isResyncing,true);
        for (let i=0;i<5;i++) {
            values[fields[i]] = {state:"ok",data:i === 2 ? {partial:"backend value"} : values[fields[i]].data};
            adapter.receiveLanguageMutation({endpoint:`/get/data/${getters[i]}`,status:200},send);
            assert.equal(adapter.canChangeLanguageSettings(),i === 4);
        }
        assert.deepEqual(values.SelectedTargetLanguages.data,{partial:"backend value"});
        assert.equal(values.LanguageMutation.data.lastVrResult.kind,"failure");
    } finally {adapter.resetLanguageMutations();}
});

test("failed GETs block stale writes; a successful retry restores editing", async () => {
    const {adapter,values,request,send} = await setup();
    try {
        const write=request();adapter.beginLanguageMutation(write);
        adapter.receiveLanguageMutation({endpoint:write.endpoint,status:500},send);
        for (const getter of getters) adapter.receiveLanguageMutation({endpoint:`/get/data/${getter}`,status:500},send);
        assert.equal(values.LanguageMutation.data.isResyncing,false);
        assert.equal(adapter.canChangeLanguageSettings(),false);
        assert.equal(adapter.beginLanguageMutation(request("stale retry")),false);
        for(let i=0;i<5;i++) {
            values[fields[i]] = {...values[fields[i]],state:"ok"};
            adapter.receiveLanguageMutation({endpoint:`/get/data/${getters[i]}`,status:200},send);
        }
        assert.equal(adapter.canChangeLanguageSettings(),true);
    } finally {adapter.resetLanguageMutations();}
});

test("timeout cannot start an old GET batch before a late failing write", async context => {
    const {adapter,values,request,calls,send} = await setup();
    context.mock.timers.enable({apis:["setTimeout"]});
    try {
        const write=request();adapter.beginLanguageMutation(write);
        context.mock.timers.tick(adapter.LANGUAGE_RESPONSE_WAIT_MS);
        assert.equal(values.LanguageMutation.data.inFlight.kind,"unconfirmed");
        assert.equal(calls.length,0);
        assert.equal(adapter.beginLanguageMutation(request("retry")),false);
        adapter.receiveLanguageMutation({endpoint:write.endpoint,status:500},send);
        assert.equal(calls.length,5);
        assert.equal(values.LanguageMutation.data.isResyncing,true);
    } finally {adapter.resetLanguageMutations();context.mock.timers.reset();}
});

test("uncertain write failures retain ownership without concurrent GETs", async () => {
    const {adapter,values,request,calls,send} = await setup();
    try {
        const write=request();adapter.beginLanguageMutation(write);
        adapter.languageMutationWriteUnconfirmed(write.requestId);
        assert.equal(values.LanguageMutation.data.inFlight.requestId,write.requestId);
        assert.equal(calls.length,0);
        values.SelectedTargetLanguages.state="ok";
        adapter.receiveLanguageMutation({endpoint:write.endpoint,status:200},send);
        adapter.languageMutationWriteUnconfirmed(write.requestId);
        assert.equal(values.LanguageMutation.data.lastVrResult.kind,"success");
    } finally {adapter.resetLanguageMutations();}
});

test("missing backend is a failure and requires current state before retry", async () => {
    const {adapter,values,request} = await setup();
    try {
        const write=request();adapter.beginLanguageMutation(write);
        adapter.failLanguageMutationBeforeSend(write.requestId);
        assert.equal(values.LanguageMutation.data.inFlight,null);
        assert.equal(values.LanguageMutation.data.lastVrResult.kind,"failure");
        assert.equal(adapter.canChangeLanguageSettings(),false);
    } finally {adapter.resetLanguageMutations();}
});

test("a PC rejection is visible without overwriting the VR request result", async () => {
    const {adapter,values,request} = await setup();
    try {
        adapter.beginLanguageMutation(request("owner"));
        assert.equal(adapter.beginLanguageMutation(request("pc", "pc")),false);
        assert.equal(values.NotificationStatus.data.status,"warning");
        assert.equal(values.LanguageMutation.data.lastVrResult,null);
    } finally {adapter.resetLanguageMutations();}
});
