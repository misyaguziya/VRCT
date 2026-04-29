import ExternalLink from "@images/external_link.svg?react";
import styles from "./HomepageLinkButton.module.scss";
import { useState } from "react";
import { MarqueeText } from "@common_components";

export const HomepageLinkButton = ({ homepage_link, speed = 40 /* px/s */ }) => {
    const [hovered, setHovered] = useState(false);

    return (
        <div className={styles.open_homepage_button_wrapper}>
            <a
                className={styles.open_homepage_button}
                href={homepage_link}
                target="_blank"
                rel="noreferrer"
                onMouseEnter={() => setHovered(true)}
                onMouseLeave={() => setHovered(false)}
            >
                <div className={styles.text_container}>
                    <MarqueeText className={styles.open_homepage_text} speed={speed} shouldAnimate={hovered} startImmediately={hovered}>
                        {homepage_link}
                    </MarqueeText>
                </div>
                <ExternalLink className={styles.external_link_svg} />
            </a>
        </div>
    );
};