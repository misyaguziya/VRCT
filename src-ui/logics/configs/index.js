import { createCategoryHook } from "./config_page_setter/ui_config_setter.js";

export const useAppearance = createCategoryHook("Appearance");
export const useDevice = createCategoryHook("Device");
export const useTranslation = createCategoryHook("Translation");
export const useTranscription = createCategoryHook("Transcription");
export const useVr = createCategoryHook("Vr");
export const useOthers = createCategoryHook("Others");
export const useAdvancedSettings = createCategoryHook("AdvancedSettings");

// Exceptional exports that are not part of SETTINGS_ARRAY or have custom logic.
export { useHotkeys } from "./config_page_setter/hotkeys/useHotkeys.js";
export { useSupporters } from "./config_page_setter/supporters/useSupporters.js";
export { usePlugins } from "./config_page_setter/plugins/usePlugins.js";

export { useSettingBoxScrollPosition } from "./config_page_setter/_aux/useSettingBoxScrollPosition.js";