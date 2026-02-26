import { useI18n } from "@useI18n";
import { useState } from "react";
import clsx from "clsx";
import styles from "./VersionLabel.module.scss";

import { useSoftwareVersion, useComputeMode } from "@logics_common";
import CopySvg from "@images/copy.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";

export const VersionLabel = ({ isCompact = false }) => {
    const [is_copied, setIsCopied] = useState(false);

    const { t } = useI18n();
    const { currentSoftwareVersion } = useSoftwareVersion();
    const { currentComputeMode } = useComputeMode();

    const is_cuda = currentComputeMode.data === "cuda";
    const software_version_number = currentSoftwareVersion.data;

    const version_label = (
        <div className={clsx(styles.version_text_container, {[styles.is_compact]: isCompact})}>
            <p className={styles.version_label}>{`v${software_version_number}`}</p>
            {is_cuda && <p className={styles.cuda_label}> CUDA</p>}
        </div>
    );

    const is_cpu = currentComputeMode.data === "cpu";

    const copyToClipboard = async () => {
        if (is_copied || isCompact) return;
        const copy_text = is_cpu ? `${software_version_number}` : `${software_version_number} CUDA`;
        await navigator.clipboard.writeText(copy_text);
        setIsCopied(true);

        setTimeout(() => {
            setIsCopied(false);
        }, 1000);
    };

    return (
        <div className={clsx(styles.container, { [styles.is_compact]: isCompact })}>
            <div className={clsx(styles.wrapper, {[styles.is_copied]: is_copied, [styles.is_compact]: isCompact})} onClick={copyToClipboard}>
                {version_label}
                {!isCompact && (
                    is_copied
                        ? <CheckMarkSvg className={styles.check_mark_svg}/>
                        : <CopySvg className={styles.copy_svg}/>
                )}
            </div>
        </div>
    );
};