// To avoid a name conflict with our own `useTranslation` function,
// rename the one from `react-i18next` to `useI18n`.
// This is aliased via `vite.config.js`, so it can be imported using `@useI18n`.
// Example:
// import { useI18n } from "@useI18n";
//
// export const useTranslation = () => {
//     const { t } = useI18n();
//     ...
// };
export { useTranslation as useI18n } from "react-i18next";