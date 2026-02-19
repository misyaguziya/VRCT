import { useRef, useEffect, useState } from "react";
import styles from "./MarqueeText.module.scss";

const MarqueeText = ({ children, speed = 40 /* px/s */, shouldAnimate = false, className = "",
    minOverflow = 12 /* px, minimum overflow to trigger */, paddingRight = 24 /* px */, initialDelay = 800 /* ms */, startImmediately = false }) => {
    const containerRef = useRef(null);
    const contentRef = useRef(null);
    const timers = useRef([]);
    const [isActive, setIsActive] = useState(false);

    useEffect(() => {
        const cleanup = () => {
            timers.current.forEach((t) => clearTimeout(t));
            timers.current = [];
            if (contentRef.current) {
                contentRef.current.style.transition = "";
                contentRef.current.style.transform = "";
            }
        };

        if (!shouldAnimate) {
            cleanup();
            setIsActive(false);
            return () => {};
        }

        const container = containerRef.current;
        const content = contentRef.current;
        if (!container || !content) return () => cleanup();

        // ensure extra right padding so scrolled content has breathing space
        content.style.paddingRight = `${paddingRight}px`;

        const overflow = content.scrollWidth - container.clientWidth;
        if (overflow <= minOverflow) {
            cleanup();
            setIsActive(false);
            return () => {};
        }

        setIsActive(true);

        let stopped = false;

        const runOnce = () => {
            if (stopped) return;
            const curOverflow = content.scrollWidth - container.clientWidth;
            const movePx = curOverflow > 0 ? curOverflow : 0;
            const duration = movePx / speed; // seconds

            // move left
            content.style.transition = `transform ${duration}s linear`;
            content.style.transform = `translateX(-${movePx}px)`;

            // after movement, pause a bit so the end is readable, then snap back
            const endPause = 600; // ms to wait after reaching end
            const wait = Math.max(200, duration * 1000) + endPause; // ms
            const t1 = setTimeout(() => {
                // snap back without transition
                content.style.transition = "none";
                content.style.transform = `translateX(0)`;
                // force reflow
                // eslint-disable-next-line @typescript-eslint/no-unused-expressions
                content.offsetHeight;
                // small initial delay before next iteration
                const t2 = setTimeout(runOnce, initialDelay);
                timers.current.push(t2);
            }, wait);

            timers.current.push(t1);
        };

        // start after an initial pause so first characters are visible
        const starterDelay = startImmediately ? 0 : initialDelay;
        const starter = setTimeout(runOnce, starterDelay);
        timers.current.push(starter);

        return () => {
            stopped = true;
            cleanup();
        };
    }, [children, speed, shouldAnimate, minOverflow, paddingRight, initialDelay]);

    return (
        <div className={`${styles.marquee} ${className}`} ref={containerRef}>
            <span className={styles.content} ref={contentRef} aria-live={isActive ? "off" : "polite"}>
                {children}
            </span>
        </div>
    );
};

export default MarqueeText;
