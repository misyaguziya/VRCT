import * as stores from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useNotificationStatus } from "@logics_common";
import { arrayToObject, arrayToIdLabel } from "@utils";

const transformResponse = (transformName, payload) => {
    if (!transformName) return payload;

    switch (transformName) {
        case "arrayToObject":
            return arrayToObject(payload);
        case "arrayToIdLabel":
            return arrayToIdLabel(payload);
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
        const deleteExportName = `delete${base}`;
        const toggleExportName = `toggle${base}`;
        const setSuccessExportName = `setSuccess${base}`;
        const deleteSuccessExportName = `deleteSuccess${base}`;

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

        const buildDelete = () => {
            return (value) => {
                if (pending) pending();
                asyncStdoutToPython(`/delete/data/${s.base_endpoint_name}`, value);
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

        const buildDeleteSuccess = (transformName) => {
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

        if (s.logics_template_id === "get_set_delete") {
            result[getExportName] = buildGet();
            result[setExportName] = buildSet();
            result[setSuccessExportName] = buildSetSuccess(s.response_transform ?? null);
            result[deleteExportName] = buildDelete();
            result[deleteSuccessExportName] = buildDeleteSuccess(s.response_transform ?? null);
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


import { useState, useEffect, useCallback, useMemo } from "react";

export const useSliderLogic = ({
    variable,
    setterFunction,
    postUpdateAction,
    min,
    max,
    step = 1,
    show_label_values = null,
    marks_step,
    setter_timing = "on_change_committed",
}) => {
    if (marks_step === undefined) {
        marks_step = step;
    }

    const [ui_value, setUiValue] = useState(variable);

    const decimalPlaces = marks_step.toString().includes('.')
        ? marks_step.toString().split('.')[1].length
        : 0;

    const labelFormatter = useCallback((value) => {
        if (show_label_values && show_label_values.length > 0) {
            return show_label_values.includes(value) ? value : "";
        }

        return value.toFixed(decimalPlaces);
    }, [show_label_values, decimalPlaces]);

    const marks = useMemo(() => {
        if (show_label_values === null) {
            return null;
        }
        return createMarks(min, max, marks_step, labelFormatter);
    }, [min, max, marks_step, labelFormatter, show_label_values]);

    let onchangeFunction;
    let onchangeCommittedFunction;

    if (setter_timing === "on_change") {
        onchangeFunction = useCallback((value) => {
            setUiValue(value);
            setterFunction(value);
        }, [setterFunction]);

        onchangeCommittedFunction = null;

    } else if (setter_timing === "on_change_committed") {
        onchangeFunction = useCallback((value) => {
            setUiValue(value);
        }, []);

        onchangeCommittedFunction = useCallback((value) => {
            setterFunction(value);
        }, [setterFunction]);
    } else {
        console.error(`Invalid 'setter_timing' value provided to useSliderLogic. Expected 'on_change' or 'on_change_committed'. Received: ${setter_timing}`);
    }

    useEffect(() => {
        if (variable !== ui_value) {
            setUiValue(variable);
        }
        if (postUpdateAction) {
            postUpdateAction();
        }
    }, [variable]);

    return {
        ui_value,
        onchangeFunction,
        onchangeCommittedFunction,
        marks,
    };
};


export const useSaveButtonLogic = ({
    variable,
    state,
    setFunction,
    deleteFunction
}) => {
    const [input_value, setInputValue] = useState(variable);

    const onChangeFunction = (value) => {
        setInputValue(value);
    };

    const saveFunction = () => {
        if (input_value === "" || input_value === null) {
            return deleteFunction();
        }
        setFunction(input_value);
    };

    useEffect(() => {
        if (state === "pending") return;
        setInputValue(variable);

    }, [variable]);

    return {
        variable: input_value,
        onChangeFunction: onChangeFunction,
        saveFunction: saveFunction,
    };
};

const createMarks = (min, max, marks_step = 1, labelFormatter = (value) => value) => {
    const marks = [];
    let variable = min;

    for (let i = 0; variable <= max; i++) {
        const fixedValue = parseFloat(variable.toFixed(10));

        marks.push({ value: fixedValue, label: `${labelFormatter(fixedValue)}` });

        variable += marks_step;
        variable = parseFloat(variable.toFixed(10));

        if (i > 1000) {
            console.error("Loop limit exceeded (1000 iterations). createMarks()");
            break;
        }
    }
    return marks;
};