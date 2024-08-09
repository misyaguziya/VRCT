import styles from "./MessageFormat.module.scss";
import { useTranslation } from "react-i18next";
import {
    useUiLanguageStatus,
    useSendMessageFormat,
    useSendMessageFormatWithT,
    useReceivedMessageFormat,
    useReceivedMessageFormatWithT,
} from "@store";
import { _Entry } from "../_atoms/_entry/_Entry";
import SwapImg from "@images/swap_icon.png";

export const MessageFormat = (props) => {
    const { currentSendMessageFormat, updateSendMessageFormat } = useSendMessageFormat();
    const { currentSendMessageFormatWithT, updateSendMessageFormatWithT } = useSendMessageFormatWithT();
    const { currentReceivedMessageFormat, updateReceivedMessageFormat } = useReceivedMessageFormat();
    const { currentReceivedMessageFormatWithT, updateReceivedMessageFormatWithT } = useReceivedMessageFormatWithT();

    let atoms = [];
    switch (props.id) {
        case "send":
            atoms = [currentSendMessageFormat, updateSendMessageFormat];
            break;

        case "send_with_t":
            atoms = [currentSendMessageFormatWithT, updateSendMessageFormatWithT];
            break;

        case "received":
            atoms = [currentReceivedMessageFormat, updateReceivedMessageFormat];
            break;

        case "received_with_t":
            atoms = [currentReceivedMessageFormatWithT, updateReceivedMessageFormatWithT];
            break;

        default:
            break;
    }

    return (
        <div className={styles.container}>
            <ExampleComponent {...props} current_format={atoms[0]} />
            <InputComponent {...props} atoms={atoms} />
            {["send_with_t", "received_with_t"].includes(props.id) && <SwapButton atoms={atoms} />}
        </div>
    );
};

const ExampleComponent = ({ id, current_format }) => {
    const { t } = useTranslation();
    const { currentUiLanguageStatus } = useUiLanguageStatus();

    const createExampleMessage = () => {
        const originalLangMessage = t("config_page.send_message_format.example_text");
        let format = current_format;

        if (["send_with_t", "received_with_t"].includes(id)) {
            const translationLocale = currentUiLanguageStatus === "en" ? "ja" : "en";
            const translatedLangMessage = t("config_page.send_message_format.example_text", { lng: translationLocale });

            return format.is_message_first
                ? `${format.before}${originalLangMessage}${format.between}${translatedLangMessage}${format.after}`
                : `${format.before}${translatedLangMessage}${format.between}${originalLangMessage}${format.after}`;
        } else {
            return `${format.before}${originalLangMessage}${format.after}`;
        }
    };

    return (
        <div className={styles.example_container}>
            <p className={styles.example_text}>{createExampleMessage()}</p>
        </div>
    );
};

const InputComponent = ({ id, atoms }) => {
    const [current, updater] = atoms;

    const handleChange = (key) => (e) => {
        updater({ ...current, [key]: e.target.value });
    };

    return (
        <div className={styles.input_wrapper}>
            <_Entry width="100%" onChange={handleChange("before")} />
            {["send_with_t", "received_with_t"].includes(id) ? (
                <>
                    <p className={styles.preset_text}>{current.is_message_first ? "[message]" : "[translation]"}</p>
                    <_Entry width="100%" onChange={handleChange("between")} />
                    <p className={styles.preset_text}>{current.is_message_first ? "[translation]" : "[message]"}</p>
                </>
            ) : (
                <p className={styles.preset_text}>[message]</p>
            )}
            <_Entry width="100%" onChange={handleChange("after")} />
        </div>
    );
};

const SwapButton = ({ atoms }) => {
    const [current, updater] = atoms;

    const swapMessageAndTranslate = () => {
        updater({ ...current, is_message_first: !current.is_message_first });
    };

    return (
        <div className={styles.swap_button_container}>
            <div className={styles.swap_button_wrapper} onClick={swapMessageAndTranslate}>
                <p className={styles.swap_text}>{current.is_message_first ? "[message]" : "[translation]"}</p>
                <img className={styles.swap_img} src={SwapImg} alt="Swap Icon" />
                <p className={styles.swap_text}>{current.is_message_first ? "[translation]" : "[message]"}</p>
            </div>
        </div>
    );
};



// const extractMessageFormat = (text) => {
//     const split_result = text.split("[message]");
//     let result_data = {
//         before: split_result[0],
//         after: split_result[1]
//     };
//     return result_data;
// };




// const extractMessageFormatWithT = (text) => {
//     const message_index = text.indexOf("[message]");
//     const translation_index = text.indexOf("[translation]");

//     let result_data = {
//         is_message_first: true,
//         before: "",
//         between: "",
//         after: ""
//     };

//     if (message_index < translation_index) {
//         const text_before_message = text.slice(0, message_index);
//         result_data.before = text_before_message;

//         const match = text.match(/\[message\](.*?)\[translation\]/);
//         if (match) {
//             const extracted_text = match[1];
//             result_data.between = extracted_text;
//         } else {
//             throw new Error("Invalid Message Format");
//         }

//         const text_after_translation = text.slice(translation_index + "[translation]".length);
//         result_data.after = text_after_translation;

//     } else if (translation_index < message_index) {
//         result_data.is_message_first = false;
//         const text_before_translation = text.slice(0, translation_index);
//         result_data.before = text_before_translation;

//         const match = text.match(/\[translation\](.*?)\[message\]/);
//         if (match) {
//             const extracted_text = match[1];
//             result_data.between = extracted_text;
//         } else {
//             throw new Error("Invalid Message Format");
//         }

//         const text_after_message = text.slice(message_index + "[message]".length);
//         result_data.after = text_after_message;

//     } else {
//         throw new Error("Invalid Message Format");
//     }

//     return result_data;
// };