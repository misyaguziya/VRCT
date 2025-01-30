import { useTranslation } from "react-i18next";
import { useState } from "react";
import { clsx } from "clsx";
import styles from "./VersionLabel.module.scss";

import { useSoftwareVersion } from "@logics_configs";
import { useComputeMode } from "@logics_common";
import CopySvg from "@images/copy.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";

export const VersionLabel = () => {
    const [is_copied, setIsCopied] = useState(false);

    const { t } = useTranslation();
    const { currentSoftwareVersion } = useSoftwareVersion();
    const { currentComputeMode } = useComputeMode();

    const version_label = currentComputeMode.data === "cpu"
        ? t("config_page.version", { version: currentSoftwareVersion.data })
        : currentComputeMode.data === "cuda"
        ? t("config_page.version", { version: currentSoftwareVersion.data }) + " CUDA"
        : t("config_page.version", { version: currentSoftwareVersion.data });

        const is_cpu = currentComputeMode.data === "cpu";

        const copyToClipboard = async () => {
            if (is_copied) return;
            const copy_text = is_cpu ? `${currentSoftwareVersion.data}` : `${currentSoftwareVersion.data} CUDA`;
            await navigator.clipboard.writeText(copy_text);
            setIsCopied(true);

            setTimeout(() => {
                setIsCopied(false);
            }, 1000);
        };


    return (
        <div className={styles.container}>
            <div className={clsx(styles.wrapper, {[styles.is_copied]: is_copied})} onClick={copyToClipboard}>
                <p className={styles.version_label}>{version_label}</p>
                {is_copied
                    ? <CheckMarkSvg className={styles.check_mark_svg}/>
                    : <CopySvg className={styles.copy_svg}/>
                }
            </div>
        </div>
    );
};