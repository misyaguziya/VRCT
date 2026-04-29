import { useRef, useEffect, useCallback, useState } from "react";
import { store } from "@store";

export const useMessageLogScroll = () => {
    const [isScrolling, setIsScrolling] = useState(false);
    const isSmoothScrollingRef = useRef(false);
    const animationFrameRef = useRef(null);

    const cancelSmoothScroll = () => {
        if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current);
            animationFrameRef.current = null;
        }
        isSmoothScrollingRef.current = false;
    };

    const scrollToBottom = useCallback((smooth = false) => {
        const element = store.log_box_ref.current;
        if (!element) return;

        const scrollHeight = element.scrollHeight - element.clientHeight;

        if (smooth) {
            cancelSmoothScroll();
            isSmoothScrollingRef.current = true;

            const duration = 100;
            const startTime = performance.now();
            const initialScrollTop = element.scrollTop;

            const scroll = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const easeInOutQuad = (t) =>
                    t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

                element.scrollTop =
                    initialScrollTop + (scrollHeight - initialScrollTop) * easeInOutQuad(progress);

                if (progress < 1) {
                    animationFrameRef.current = requestAnimationFrame(scroll);
                } else {
                    isSmoothScrollingRef.current = false;
                }
            };

            animationFrameRef.current = requestAnimationFrame(scroll);
        } else {
            cancelSmoothScroll();
            element.scrollTop = scrollHeight;

        }
    }, []);

    useEffect(() => {
        const handleScroll = () => {
            if (isSmoothScrollingRef.current) return;

            const element = store.log_box_ref.current;
            if (!element) return;

            const atBottom =
                Math.abs(element.scrollHeight - element.scrollTop - element.clientHeight) < 5;

            setIsScrolling(!atBottom);
        };

        const element = store.log_box_ref.current;
        if (element) {
            element.addEventListener("scroll", handleScroll);
        }

        return () => {
            if (element) {
                element.removeEventListener("scroll", handleScroll);
            }
            cancelSmoothScroll();
        };
    }, []);

    return {
        scrollToBottom,
        isScrolling,
    };
};
