import { getDefaultStore } from "jotai";
import i18next from "i18next";
import { Atom_LanguageMutation, Atom_NotificationStatus, Atom_SelectedPresetTabNumber, Atom_SelectedYourLanguages,
    Atom_SelectedTargetLanguages, Atom_SelectedTranslationEngines, Atom_TranslationEngines } from "@store";
import { createLanguageMutationCoordinator, isLanguageMutation } from "./languageMutationCoordinator";

export { isLanguageMutation };
export const LANGUAGE_RESPONSE_WAIT_MS = 30000;
const jotai = getDefaultStore();
const snapshotAtoms = { tab: Atom_SelectedPresetTabNumber, your: Atom_SelectedYourLanguages,
    target: Atom_SelectedTargetLanguages, selectedEngines: Atom_SelectedTranslationEngines };
const getAtoms = { "/get/data/selected_tab_no": Atom_SelectedPresetTabNumber,
    "/get/data/selected_your_languages": Atom_SelectedYourLanguages,
    "/get/data/selected_target_languages": Atom_SelectedTargetLanguages,
    "/get/data/selected_translation_engines": Atom_SelectedTranslationEngines,
    "/get/data/selectable_translation_engines": Atom_TranslationEngines };
const affectedAtoms = endpoint => endpoint.endsWith("selected_tab_no") ? [Atom_SelectedPresetTabNumber]
    : endpoint.endsWith("selected_your_languages") ? [Atom_SelectedYourLanguages]
        : endpoint.endsWith("selected_target_languages") ? [Atom_SelectedTargetLanguages]
            : endpoint.endsWith("selected_translation_engines") ? [Atom_SelectedTranslationEngines]
                : [Atom_SelectedYourLanguages, Atom_SelectedTargetLanguages];
const setState = (atoms, state) => atoms.forEach(atom => jotai.set(atom, old => ({ ...old, state })));
const resyncPending = new Set();
const publish = data => jotai.set(Atom_LanguageMutation, { state: "ok", data: { ...data, isResyncing: resyncPending.size > 0 } });
const coordinator = createLanguageMutationCoordinator(publish, request => {
    if (request.source !== "pc") return;
    jotai.set(Atom_NotificationStatus, { state: "ok", data: {
        status: "warning", is_open: true, category_id: null,
        message: i18next.t("vr_panel.language.pc_retry"), options: {},
    } });
});
let timer;
const clearTimer = () => { clearTimeout(timer); timer = undefined; };

export const createLanguageRequestId = () => crypto.randomUUID();
export const getLanguageSnapshot = () => Object.fromEntries(Object.entries(snapshotAtoms).map(([key, atom]) => [key, jotai.get(atom).data]));
export const canChangeLanguageSettings = () => !jotai.get(Atom_LanguageMutation).data.inFlight
    && !jotai.get(Atom_LanguageMutation).data.isResyncing
    && Object.values(getAtoms).every(atom => jotai.get(atom).state === "ok");

export function resyncLanguageSettings(send) {
    Object.keys(getAtoms).forEach(endpoint => resyncPending.add(endpoint));
    publish(coordinator.getState());
    setState(Object.values(getAtoms), "pending");
    for (const [endpoint, atom] of Object.entries(getAtoms)) {
        const failed = () => { setState([atom], "error"); finishResync(endpoint); };
        send(endpoint).then(sent => { if (sent === false) failed(); }).catch(failed);
    }
}

function finishResync(endpoint) {
    if (!resyncPending.delete(endpoint)) return;
    if (resyncPending.size === 0) publish(coordinator.getState());
}

export function rejectLanguageMutation(request, reason) {
    if (request && isLanguageMutation(request.endpoint)) coordinator.reject(request, reason);
}

export function failLanguageRead(endpoint) {
    if (!getAtoms[endpoint]) return;
    setState([getAtoms[endpoint]], "error");
    finishResync(endpoint);
}

export function beginLanguageMutation(request) {
    if (resyncPending.size > 0 || Object.values(getAtoms).some(atom => jotai.get(atom).state !== "ok")) {
        coordinator.reject(request, "syncing");
        return false;
    }
    if (!coordinator.begin(request, getLanguageSnapshot())) return false;
    setState(affectedAtoms(request.endpoint), "pending");
    clearTimer();
    timer = setTimeout(() => {
        coordinator.markUnconfirmed(request.requestId, "timeout");
    }, LANGUAGE_RESPONSE_WAIT_MS);
    return true;
}

export function failLanguageMutationBeforeSend(requestId) {
    const request = coordinator.failBeforeSend(requestId, "backend-unavailable");
    if (!request) return;
    clearTimer();
    setState(affectedAtoms(request.endpoint), "error");
}

export function languageMutationWriteUnconfirmed(requestId) {
    if (!coordinator.markUnconfirmed(requestId, "write-unconfirmed")) return;
    clearTimer();
    // A GET while the write is still running can return its previous value.
    // Keep ownership and wait for the final response before fetching state.
}

export function receiveLanguageMutation(response, send) {
    const active = coordinator.getState().inFlight;
    // Publish resynchronization before releasing ownership / publishing failure.
    // VR receives atom changes as separate events, so it must never see a gap
    // between failed completion and the subsequent GETs.
    if (active?.endpoint === response.endpoint && [400, 404, 423, 500].includes(response.status)) resyncLanguageSettings(send);
    const request = coordinator.complete(response);
    if (request) {
        clearTimer();
    } else if (response.status !== 200 && getAtoms[response.endpoint]) {
        setState([getAtoms[response.endpoint]], "error");
    }
    if (getAtoms[response.endpoint]) finishResync(response.endpoint);
}

export function resetLanguageMutations() { clearTimer(); resyncPending.clear(); coordinator.reset(); }
