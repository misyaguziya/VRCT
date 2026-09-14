import { useState } from "react";
import clsx from "clsx";
import styles from "./VersionLabel.module.scss";

import { useSoftwareVersion, useComputeMode } from "@logics_common";
import CopySvg from "@images/copy.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";

export const VersionLabel = ({ isCompact = false }) => {
    const [is_copied, setIsCopied] = useState(false);

    const { currentSoftwareVersion } = useSoftwareVersion();
    const { currentComputeMode } = useComputeMode();

    const is_cuda = currentComputeMode.data === "cuda";
    const software_version_number = currentSoftwareVersion.data || "";

    const is_beta = software_version_number.toLowerCase().includes("beta");
    const base_version = software_version_number.split("-")[0];

    const copyToClipboard = async () => {
        if (is_copied || isCompact) return;
        const copy_text = is_cuda ? `${software_version_number} CUDA` : `${software_version_number}`;
        await navigator.clipboard.writeText(copy_text);
        setIsCopied(true);

        setTimeout(() => {
            setIsCopied(false);
        }, 1000);
    };

    const is_two_line_expanded = !isCompact && is_beta && is_cuda;

    return (
        <div
            className={clsx(styles.container, {
                [styles.is_compact]: isCompact,
                [styles.is_beta]: is_beta,
                [styles.is_cuda]: is_cuda,
            })}
        >
            <div
                className={clsx(styles.wrapper, {
                    [styles.is_copied]: is_copied,
                    [styles.is_compact]: isCompact,
                })}
                onClick={copyToClipboard}
            >
                {isCompact ? (
                    <div className={styles.compact_content}>
                        <p className={styles.compact_version_label}>{`v${base_version}`}</p>
                        {is_beta && <span className={styles.compact_badge}>Beta</span>}
                        {is_cuda && <span className={styles.compact_badge}>CUDA</span>}
                    </div>
                ) : (
                    <div className={styles.expanded_row}>
                        <div className={styles.version_text_block}>
                            <p className={styles.version_label}>
                                {`v${software_version_number}`}
                                {!is_beta && is_cuda && <span className={styles.inline_cuda}> CUDA</span>}
                            </p>
                            {is_two_line_expanded && (
                                <p className={styles.second_line_cuda}>CUDA</p>
                            )}
                        </div>
                        {is_copied ? (
                            <CheckMarkSvg className={styles.check_mark_svg} />
                        ) : (
                            <CopySvg className={styles.copy_svg} />
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};