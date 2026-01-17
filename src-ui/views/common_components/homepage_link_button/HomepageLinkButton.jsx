import ExternalLink from "@images/external_link.svg?react";
import styles from "./HomepageLinkButton.module.scss";
import { useRef, useState, useCallback } from "react";

export const HomepageLinkButton = ({ homepage_link, speed = 40 /* px/s */ }) => {
    const containerRef = useRef(null);
    const textRef = useRef(null);
    const [inlineStyle, setInlineStyle] = useState({});

    const handleMouseEnter = useCallback(() => {
        const container = containerRef.current;
        const text = textRef.current;
        if (!container || !text) return;
        const overflow = text.scrollWidth - container.clientWidth;
        if (overflow > 0) {
            const duration = overflow / speed;
            setInlineStyle({
                transform: `translateX(-${overflow}px)`,
                transition: `transform ${duration}s linear`,
            });
        }
    }, [speed]);

    const handleMouseLeave = useCallback(() => {
        setInlineStyle({
            transform: 'translateX(0)',
            transition: 'transform 0.3s ease-out',
        });
    }, []);

    return (
        <div className={styles.open_homepage_button_wrapper}>
            <a
                className={styles.open_homepage_button}
                href={homepage_link}
                target="_blank"
                rel="noreferrer"
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
            >
                <div className={styles.text_container} ref={containerRef}>
                    <p
                    className={styles.open_homepage_text}
                    ref={textRef}
                    style={inlineStyle}
                    >
                    {homepage_link}
                    </p>
                </div>
                <ExternalLink className={styles.external_link_svg} />
            </a>
        </div>
    );
};