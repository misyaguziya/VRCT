import { useTranslation } from "react-i18next";
import CircularProgress from "@mui/material/CircularProgress";
import styles from "./DownloadModels.module.scss";
import {
    RadioButton,
} from "../index";

export const DownloadModels = (props) => {
    const options = props.options.map(item => ({
        ...item,
        disabled: !item.is_downloaded
    }));

    return (
        <>
            <RadioButton
                selectFunction={props.selectFunction}
                name={props.name}
                options={options}
                checked_variable={props.checked_variable}
                column={true}
                ChildComponent={ModelSelector}
                downloadStartFunction={props.downloadStartFunction}
            />
        </>
    );
};

const ModelSelector = ({option, ...props}) => {
    const { t } = useTranslation();

    const renderContent = () => {
        const circular_progress = Math.floor(option.progress / 10) * 10;

        switch (true) {
            case option.progress !== null:
                return (
                    <>
                        <CircularProgress
                            variant={(option.progress === 100) ? "indeterminate" : "determinate"}
                            value={circular_progress}
                            size="3rem"
                            sx={{ color: "var(--primary_300_color)" }}
                        />
                        <p className={styles.progress_label}>{`${Math.round(option.progress)}%`}</p>
                    </>
                );
            case option.is_pending:
                return <CircularProgress size="3rem" sx={{ color: "var(--dark_600_color)" }}/>;
            case !option.is_downloaded:
                return (
                    <button
                        className={styles.download_button}
                        onClick={() => props.downloadStartFunction(option.id)}
                    >
                        <p className={styles.download_button_label}>{t("config_page.model_download_button_label")}</p>
                    </button>
                );
            default:
                return null;
        }
    };

    return <div className={styles.download_container}>{renderContent()}</div>;
};
