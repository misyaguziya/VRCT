export const LANGUAGE_MUTATION_ENDPOINTS = [
    "/set/data/selected_tab_no",
    "/set/data/selected_your_languages",
    "/set/data/selected_target_languages",
    "/set/data/selected_translation_engines",
    "/run/swap_your_language_and_target_language",
];

export const isLanguageMutation = endpoint => LANGUAGE_MUTATION_ENDPOINTS.includes(endpoint);

// キーの順に左右されない文字列にする。VR画面からの要求は Tauri の emit を通るとキーが辞書順に並び替わる
// (serde_json の Value は順序を保たない) ため、JSON.stringify の素の比較では内容が同じでも食い違う
const canonical = value => JSON.stringify(value, (_key, v) =>
    v && typeof v === "object" && !Array.isArray(v)
        ? Object.fromEntries(Object.keys(v).sort().map(key => [key, v[key]]))
        : v);
export const sameSnapshot = (a, b) => canonical(a) === canonical(b);

// The backend has no request IDs. Admit only one language write across PC and VR,
// and retain its ownership until a final response, even after a timeout.
export function createLanguageMutationCoordinator(publish, onReject = () => {}) {
    let state = { inFlight: null, lastVrResult: null };
    const result = (request, kind, extra = {}) => {
        if (request.source === "vr") {
            state = { ...state, lastVrResult: { requestId: request.requestId, endpoint: request.endpoint, kind, ...extra } };
        }
        publish(state);
    };
    return {
        getState: () => state,
        reject(request, reason) {
            // 実機で「言語を変えられなかった」原因を後から追えるよう、メイン画面のコンソールに理由を残す
            console.warn("[language] rejected", reason, request.endpoint, request.source);
            result(request, "rejected", { reason }); onReject(request, reason);
        },
        begin(request, snapshot) {
            if (!isLanguageMutation(request.endpoint)) return false;
            if (state.inFlight) { this.reject(request, "busy"); return false; }
            if (!sameSnapshot(request.expectedSnapshot, snapshot)) {
                this.reject(request, "stale"); return false;
            }
            state = { ...state, inFlight: { ...request, kind: "saving" } };
            publish(state);
            return true;
        },
        complete(response) {
            const request = state.inFlight;
            if (!request || response.endpoint !== request.endpoint || ![200, 400, 404, 423, 500].includes(response.status)) return null;
            state = { ...state, inFlight: null };
            if (response.status !== 200) console.warn("[language] failed", response.status, response.endpoint);
            result(request, response.status === 200 ? "success" : "failure", { status: response.status });
            return request;
        },
        failBeforeSend(requestId, reason) {
            const request = state.inFlight;
            if (!request || request.requestId !== requestId) return null;
            state = { ...state, inFlight: null };
            console.warn("[language] failed before send", reason, request.endpoint);
            result(request, "failure", { reason });
            return request;
        },
        markUnconfirmed(requestId, reason) {
            const request = state.inFlight;
            if (!request || request.requestId !== requestId) return false;
            state = { ...state, inFlight: { ...request, kind: "unconfirmed" } };
            result(request, "unconfirmed", { reason });
            return true;
        },
        reset() {
            const request = state.inFlight;
            state = { ...state, inFlight: null };
            if (request) result(request, "failure", { reason: "backend-restarted" });
            else publish(state);
        },
    };
}
