import { useI18n } from "@useI18n";

import {
    useTranslation,

    useSaveButtonLogic,
} from "@logics_configs";

import {
    DownloadModelsContainer,
    AuthKeyContainer,
    EntryWithSaveButtonContainer,
    DropdownMenuContainer,
    ConnectionCheckButtonContainer,
} from "../_templates/Templates";

import { ComputeDevice } from "../_components/compute_device/ComputeDevice";

import {
    deepl_auth_key_url,
    plamo_auth_key_url,
    gemini_auth_key_url,
    openai_auth_key_url,
    groq_auth_key_url,
    openrouter_auth_key_url,
} from "@ui_configs";

import { useLLMConnection } from "@logics_common";

export const Translation = () => {
    return (
        <>
            <CTranslate2WeightType_Box />
            <TranslationComputeDevice_Box />

            <DeepLAuthKey_Box />

            <PlamoAuthKey_Box />
            <PlamoModelContainer />

            <GeminiAuthKey_Box />
            <GeminiModelContainer />

            <OpenAIAuthKey_Box />
            <OpenAIModelContainer />

            <GroqAuthKey_Box />
            <GroqModelContainer />

            <OpenRouterAuthKey_Box />
            <OpenRouterModelContainer />

            <LMStudioConnectionCheck_Box />
            <LMStudioURL_Box />
            <LMStudioModelContainer />

            <OllamaConnectionCheck_Box />
            <OllamaModelContainer />
        </>
    );
};

const CTranslate2WeightType_Box = () => {
    const { t } = useI18n();
    const {
        currentCTranslate2WeightTypeStatus,
        pendingCTranslate2WeightTypeStatus,
        downloadCTranslate2WeightTypeStatus,

        currentSelectedCTranslate2WeightType,
        setSelectedCTranslate2WeightType,
    } = useTranslation();

    const selectFunction = (id) => {
        setSelectedCTranslate2WeightType(id);
    };

    const downloadStartFunction = (id) => {
        pendingCTranslate2WeightTypeStatus(id);
        downloadCTranslate2WeightTypeStatus(id);
    };


    const c_translate2_weight_types_object = currentCTranslate2WeightTypeStatus.data.map(item => {
        return {
            ...item,
            label: `${item.id} (${item.capacity})`,
        };
    });


    return (
        <>
            <DownloadModelsContainer
                label={t(
                    "config_page.translation.ctranslate2_weight_type.label",
                    {ctranslate2: "CTranslate2"}
                )}
                desc={t(
                    "config_page.translation.ctranslate2_weight_type.desc",
                    {ctranslate2: "CTranslate2"}
                )}
                name="ctranslate2_weight_type"
                options={c_translate2_weight_types_object}
                checked_variable={currentSelectedCTranslate2WeightType}
                selectFunction={selectFunction}
                downloadStartFunction={downloadStartFunction}
            />
        </>
    );
};

const TranslationComputeDevice_Box = () => {
    const { t } = useI18n();
    const {
        currentSelectableTranslationComputeDeviceList,
        currentSelectedTranslationComputeDevice,
        setSelectedTranslationComputeDevice,
        currentSelectedTranslationComputeType,
        setSelectedTranslationComputeType,
    } = useTranslation();

    return (
        <ComputeDevice
            label={t("config_page.translation.translation_compute_device.label")}
            dropdownIdPrefix="translation"
            currentDeviceList={currentSelectableTranslationComputeDeviceList}
            currentSelectedDevice={currentSelectedTranslationComputeDevice}
            setSelectedDevice={setSelectedTranslationComputeDevice}
            currentSelectedComputeType={currentSelectedTranslationComputeType}
            setSelectedComputeType={setSelectedTranslationComputeType}
        />
    );
};

const DeepLAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentDeepLAuthKey, setDeepLAuthKey, deleteDeepLAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentDeepLAuthKey.data,
        state: currentDeepLAuthKey.state,
        setFunction: setDeepLAuthKey,
        deleteFunction: deleteDeepLAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.deepl_auth_key.label")}
                desc={t(
                    "config_page.translation.deepl_auth_key.desc",
                    {translator: t("main_page.translator")}
                )}
                webpage_url={deepl_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentDeepLAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
            />
        </>
    );
};

const PlamoAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentPlamoAuthKey, setPlamoAuthKey, deletePlamoAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentPlamoAuthKey.data,
        state: currentPlamoAuthKey.state,
        setFunction: setPlamoAuthKey,
        deleteFunction: deletePlamoAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.plamo_auth_key.label")}
                // desc="Plamo Auth Desc"
                webpage_url={plamo_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentPlamoAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const PlamoModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectablePlamoModelList,

        currentSelectedPlamoModel,
        setSelectedPlamoModel,

        currentPlamoAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedPlamoModel(selected_data.selected_id);
    };


    let selected_label = (!currentPlamoAuthKey.data && !currentSelectedPlamoModel.data) ? t("config_page.common.correct_auth_key_required") : currentSelectedPlamoModel.data;


    return (
        <DropdownMenuContainer
            dropdown_id="select_plamo_model"
            label={t("config_page.translation.select_plamo_model.label")}
            selected_id={selected_label}
            list={currentSelectablePlamoModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedPlamoModel.state}
            is_disabled={!currentPlamoAuthKey.data}
        />
    );
};



const GeminiAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentGeminiAuthKey, setGeminiAuthKey, deleteGeminiAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentGeminiAuthKey.data,
        state: currentGeminiAuthKey.state,
        setFunction: setGeminiAuthKey,
        deleteFunction: deleteGeminiAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.gemini_auth_key.label")}
                // desc="Gemini Auth Desc"
                webpage_url={gemini_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentGeminiAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const GeminiModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableGeminiModelList,

        currentSelectedGeminiModel,
        setSelectedGeminiModel,

        currentGeminiAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedGeminiModel(selected_data.selected_id);
    };

    let selected_label = (!currentGeminiAuthKey.data && !currentSelectedGeminiModel.data)
        ? t("config_page.common.correct_auth_key_required")
        : currentSelectedGeminiModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_gemini_model"
            label={t("config_page.translation.select_gemini_model.label")}
            selected_id={selected_label}
            list={currentSelectableGeminiModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedGeminiModel.state}
            is_disabled={!currentGeminiAuthKey.data}
        />
    );
};


const OpenAIAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentOpenAIAuthKey, setOpenAIAuthKey, deleteOpenAIAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentOpenAIAuthKey.data,
        state: currentOpenAIAuthKey.state,
        setFunction: setOpenAIAuthKey,
        deleteFunction: deleteOpenAIAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.openai_auth_key.label")}
                // desc="OpenAI Auth Desc"
                webpage_url={openai_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentOpenAIAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const OpenAIModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableOpenAIModelList,

        currentSelectedOpenAIModel,
        setSelectedOpenAIModel,

        currentOpenAIAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedOpenAIModel(selected_data.selected_id);
    };

    let selected_label = (!currentOpenAIAuthKey.data && !currentSelectedOpenAIModel.data)
        ? t("config_page.common.correct_auth_key_required")
        : currentSelectedOpenAIModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_openai_model"
            label={t("config_page.translation.select_openai_model.label")}
            selected_id={selected_label}
            list={currentSelectableOpenAIModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedOpenAIModel.state}
            is_disabled={!currentOpenAIAuthKey.data}
        />
    );
};


const GroqAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentGroqAuthKey, setGroqAuthKey, deleteGroqAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentGroqAuthKey.data,
        state: currentGroqAuthKey.state,
        setFunction: setGroqAuthKey,
        deleteFunction: deleteGroqAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.groq_auth_key.label")}
                // desc="Groq Auth Desc"
                webpage_url={groq_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentGroqAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const GroqModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableGroqModelList,

        currentSelectedGroqModel,
        setSelectedGroqModel,

        currentGroqAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedGroqModel(selected_data.selected_id);
    };

    let selected_label = (!currentGroqAuthKey.data && !currentSelectedGroqModel.data)
        ? t("config_page.common.correct_auth_key_required")
        : currentSelectedGroqModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_groq_model"
            label={t("config_page.translation.select_groq_model.label")}
            selected_id={selected_label}
            list={currentSelectableGroqModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedGroqModel.state}
            is_disabled={!currentGroqAuthKey.data}
        />
    );
};


const OpenRouterAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentOpenRouterAuthKey, setOpenRouterAuthKey, deleteOpenRouterAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentOpenRouterAuthKey.data,
        state: currentOpenRouterAuthKey.state,
        setFunction: setOpenRouterAuthKey,
        deleteFunction: deleteOpenRouterAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.openrouter_auth_key.label")}
                // desc="OpenRouter Auth Desc"
                webpage_url={openrouter_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentOpenRouterAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const OpenRouterModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableOpenRouterModelList,

        currentSelectedOpenRouterModel,
        setSelectedOpenRouterModel,

        currentOpenRouterAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedOpenRouterModel(selected_data.selected_id);
    };

    let selected_label = (!currentOpenRouterAuthKey.data && !currentSelectedOpenRouterModel.data)
        ? t("config_page.common.correct_auth_key_required")
        : currentSelectedOpenRouterModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_openrouter_model"
            label={t("config_page.translation.select_openrouter_model.label")}
            selected_id={selected_label}
            list={currentSelectableOpenRouterModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedOpenRouterModel.state}
            is_disabled={!currentOpenRouterAuthKey.data}
        />
    );
};

const LMStudioConnectionCheck_Box = () => {
    const { t } = useI18n();
    const { currentIsLMStudioConnected, checkConnection_LMStudio } = useLLMConnection();

    return (
        <>
            <ConnectionCheckButtonContainer
                label={t("config_page.translation.lmstudio_connection_check.label")}
                variable={currentIsLMStudioConnected.data}
                state={currentIsLMStudioConnected.state}
                checkFunction={checkConnection_LMStudio}
                remove_border_bottom={true}
                // width="10rem"
            />
        </>
    );
};
const LMStudioURL_Box = () => {
    const { t } = useI18n();
    const { currentLMStudioURL, setLMStudioURL, deleteLMStudioURL } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentLMStudioURL.data,
        state: currentLMStudioURL.state,
        setFunction: setLMStudioURL,
        deleteFunction: deleteLMStudioURL,
    });

    return (
        <>
            <EntryWithSaveButtonContainer
                label="LM Studio URL"
                // label={t("config_page.translation.lmstudio_url.label")}
                // desc={t("config_page.translation.lmstudio_url.desc")}
                variable={variable}
                saveFunction={saveFunction}
                onChangeFunction={onChangeFunction}
                state={currentLMStudioURL.state}
                remove_border_bottom={true}
                // width="10rem"
            />
        </>
    );
};
const LMStudioModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableLMStudioModelList,

        currentSelectedLMStudioModel,
        setSelectedLMStudioModel,
    } = useTranslation();

    const { currentIsLMStudioConnected } = useLLMConnection();

    const selectFunction = (selected_data) => {
        setSelectedLMStudioModel(selected_data.selected_id);
    };

    let selected_label = (!currentIsLMStudioConnected.data && !currentSelectedLMStudioModel.data)
        ? t("config_page.translation.select_lmstudio_model.connection_required")
        : currentSelectedLMStudioModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_lmstudio_model"
            label={t("config_page.translation.select_lmstudio_model.label")}
            selected_id={selected_label}
            list={currentSelectableLMStudioModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedLMStudioModel.state}
            is_disabled={!currentIsLMStudioConnected.data}
        />
    );
};

const OllamaConnectionCheck_Box = () => {
    const { t } = useI18n();
    const { currentIsOllamaConnected, checkConnection_Ollama } = useLLMConnection();

    return (
        <>
            <ConnectionCheckButtonContainer
                label={t("config_page.translation.ollama_connection_check.label")}
                variable={currentIsOllamaConnected.data}
                state={currentIsOllamaConnected.state}
                checkFunction={checkConnection_Ollama}
                remove_border_bottom={true}
                // width="10rem"
            />
        </>
    );
};
const OllamaModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableOllamaModelList,

        currentSelectedOllamaModel,
        setSelectedOllamaModel,
    } = useTranslation();

    const { currentIsOllamaConnected } = useLLMConnection();

    const selectFunction = (selected_data) => {
        setSelectedOllamaModel(selected_data.selected_id);
    };

    let selected_label = (!currentIsOllamaConnected.data && !currentSelectedOllamaModel.data)
        ? t("config_page.translation.select_ollama_model.connection_required")
        : currentSelectedOllamaModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_ollama_model"
            label={t("config_page.translation.select_ollama_model.label")}
            selected_id={selected_label}
            list={currentSelectableOllamaModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedOllamaModel.state}
            is_disabled={!currentIsOllamaConnected.data}
        />
    );
};

