import styles from "./MessageFormat.module.scss";
import { useTranslation } from "react-i18next";

export const MessageFormat = (props) => {

    return (
        <div className={styles.container}>
            <ExampleComponent {...props}/>
            <InputComponent {...props}/>
            {
                props.with_t
                ? <SwapButton/>
                : null
            }
        </div>
    );
};

const ExampleComponent = (props) => {
    const { t } = useTranslation();

    const createExampleMessage = () => {
        return t("config_window.send_message_format.example_text");
    };

    return (
        <div className={styles.example_container}>
            <p className={styles.example_text}>{createExampleMessage()}</p>
        </div>
    );
};


import { _Entry } from "../_atoms/_Entry";
const InputComponent = (props) => {
    const { t } = useTranslation();

    const onChangeInput = (e) => {
        console.log(e.target.value);
    };

    return (
        <div className={styles.input_wrapper}>
            <_Entry width="100%" onChange={onChangeInput} />
            <p className={styles.preset_text}>[message]</p>
            <_Entry width="100%" onChange={onChangeInput} />
            {
                props.with_t
                ? (<>
                    <p className={styles.preset_text}>[translation]</p>
                    <_Entry width="100%" onChange={onChangeInput} />
                    </>)
                : null
            }
        </div>
    );
};


import SwapImg from "@images/swap_icon.png";
const SwapButton = () => {
    const swapMessageAndTranslate = () => {

    };

    return (
        <div className={styles.swap_button_container}>
            <div className={styles.swap_button_wrapper} onClick={swapMessageAndTranslate}>
                <p className={styles.swap_text}>[message]</p>
                <img className={styles.swap_img} src={SwapImg} />
                <p className={styles.swap_text}>[translate]</p>
            </div>
        </div>

    );
};