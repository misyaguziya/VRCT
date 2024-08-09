import styles from "./RightSideComponents.module.scss";

import HelpSvg from "@images/help.svg?react";

export const RightSideComponents = () => {
    return (
        <div className={styles.container}>
            <p>VRC mic mute sync</p>
            <p>Overlay(VR)</p>
            <a
            className={styles.help_and_info_button}
            href="https://mzsoftware.notion.site/VRCT-Documents-be79b7a165f64442ad8f326d86c22246"
            target="_blank"
            rel="noreferrer"
            >
                <HelpSvg className={styles.help_svg} />
            </a>
        </div>
    );
};