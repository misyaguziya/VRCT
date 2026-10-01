export const LANGUAGE_MUTATION_ENDPOINTS = [
    "/set/data/selected_tab_no",
    "/set/data/selected_your_languages",
    "/set/data/selected_target_languages",
    "/set/data/selected_translation_engines",
    "/run/swap_your_language_and_target_language",
];

export const isLanguageMutation = endpoint => LANGUAGE_MUTATION_ENDPOINTS.includes(endpoint);

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
        reject(request, reason) { result(request, "rejected", { reason }); onReject(request, reason); },
        begin(request, snapshot) {
            if (!isLanguageMutation(request.endpoint)) return false;
            if (state.inFlight) { this.reject(request, "busy"); return false; }
            if (JSON.stringify(request.expectedSnapshot) !== JSON.stringify(snapshot)) {
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
            result(request, response.status === 200 ? "success" : "failure", { status: response.status });
            return request;
        },
        failBeforeSend(requestId, reason) {
            const request = state.inFlight;
            if (!request || request.requestId !== requestId) return null;
            state = { ...state, inFlight: null };
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
