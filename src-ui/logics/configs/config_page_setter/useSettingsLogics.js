import * as stores from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useNotificationStatus } from "@logics_common";
import { arrayToObject } from "@utils";

const transformResponse = (transformName, payload) => {
    if (!transformName) return payload;

    switch (transformName) {
        case "arrayToObject":
            return arrayToObject(payload);
        default:
            return payload;
    }
};

export const useSettingsLogics = (settingsArray, Category) => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { showNotification_SaveSuccess } = useNotificationStatus();

    const filtered = settingsArray.filter((s) => s.Category === Category);
    const result = {};


    for (const s of filtered) {
        const base = s.Base_Name;
        let storeHook = undefined;

        if (typeof stores.getStoreHook === "function") {
            storeHook = stores.getStoreHook(base);
        }

        if (!storeHook) {
            const hookName = `useStore_${base}`;
            storeHook = stores[hookName];
        }

        if (!storeHook) {
            console.warn(`[useSettingsLogics] store hook not found for ${base}`);
            continue;
        }

        const store = storeHook();

        const currentKey = `current${base}`;
        const updateKey = `update${base}`;
        const pendingKey = `pending${base}`;

        const current = store[currentKey];
        const update = store[updateKey];
        const pending = store[pendingKey];

        const currentExportName = `current${base}`;
        const updateExportName = `update${base}`;
        const updateFromBackendExportName = `updateFromBackend${base}`;
        const getExportName = `get${base}`;
        const setExportName = `set${base}`;
        const toggleExportName = `toggle${base}`;
        const setSuccessExportName = `setSuccess${base}`;

        const runExportName = `runSuccess${base}`;

        // To use by UI------------------------------------
        const buildGet = () => {
            return () => {
                if (pending) pending();
                asyncStdoutToPython(`/get/data/${s.base_endpoint_name}`);
            };
        };

        const buildSet = () => {
            return (value) => {
                if (pending) pending();
                asyncStdoutToPython(`/set/data/${s.base_endpoint_name}`, value);
            };
        };

        const buildRun = () => {
            return () => {
                asyncStdoutToPython(`/run/${s.base_endpoint_name}`);
            };
        };


        // To use a response from backend------------------------------------
        const buildSetSuccess = (transformName) => {
            return (payload) => {
                const transformed = transformResponse(transformName, payload);
                if (update) update(transformed);
                showNotification_SaveSuccess();
            };
        };

        const buildUpdateFromBackend = (transformName) => {
            return (payload) => {
                const transformed = transformResponse(transformName, payload);
                if (update) update(transformed);
            };
        };


        result[currentExportName] = current;
        result[updateExportName] = update;
        result[updateFromBackendExportName] = buildUpdateFromBackend(s.response_transform ?? null);

        if (s.add_endpoint_run_array?.includes("to_backend")) {
            result[runExportName] = buildRun();
        }


        if (s.logics_template_id === "get_list") {
            result[getExportName] = buildGet();
            continue;
        }

        if (s.logics_template_id === "get_set") {
            result[getExportName] = buildGet();
            result[setExportName] = buildSet();
            result[setSuccessExportName] = buildSetSuccess(s.response_transform ?? null);
            continue;
        }

        if (s.logics_template_id === "toggle_enable_disable") {
            result[getExportName] = buildGet();
            result[toggleExportName] = () => {
                if (pending) pending();
                const isOn = current && current.data;
                if (isOn) {
                    asyncStdoutToPython(`/set/disable/${s.base_endpoint_name}`);
                } else {
                    asyncStdoutToPython(`/set/enable/${s.base_endpoint_name}`);
                }
            };

            result[setSuccessExportName] = buildSetSuccess(s.response_transform ?? null);
            continue;
        }

        if (s.logics_template_id === "weight_download_status") {
            result[setSuccessExportName] = buildSetSuccess(s.response_transform ?? null);

            result[`updateDownloadProgress${base}`] = (payload) => {
                update((old_status) => {
                    return old_status.data.map((item) =>
                        payload.weight_type === item.id
                            ? { ...item, progress: payload.progress * 100 }
                            : item
                    );
                });
            };
            result[`updateDownloaded${base}`] = (downloaded_weight_type_status) => {
                update((old_status) => {
                    return old_status.data.map((item) => ({
                        ...item,
                        is_downloaded: downloaded_weight_type_status[item.id] ?? item.is_downloaded,
                    }));
                });
            };
            result[`pending${base}`] = (id) => {
                update((old_status) => {
                    return old_status.data.map((item) =>
                        id === item.id
                            ? { ...item, is_pending: true }
                            : item
                    );
                });
            };
            result[`downloaded${base}`] = (id) => {
                update((old_status) => {
                    return old_status.data.map((item) =>
                        id === item.id
                            ? { ...item, is_downloaded: true, is_pending: false, progress: null }
                            : item
                    );
                });
            };

            result[`download${base}`] = (weight_type) => {
                asyncStdoutToPython(`/run/download_${s.base_endpoint_name}`, weight_type);
            };

            continue;
        }
    }

    return { settings: result };
};


export const useConfigFunctions = (Category) => {
    const { asyncStdoutToPython } = useStdoutToPython();

    switch (Category) {
        case "Vr":
            return {
                sendTextToOverlay: (text) => {
                    asyncStdoutToPython("/run/send_text_overlay", text);
                },
            };
        default:
            return {};
    }
};