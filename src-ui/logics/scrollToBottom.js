export const scrollToBottom = (ref, smooth = false) => {
    const element = ref.current;
    const scroll_height = element.scrollHeight - element.clientHeight;

    if (smooth) {
        const duration = 300; // スクロールにかける時間（ミリ秒）
        const start_time = performance.now();
        const scroll_top = element.scrollTop;

        const scroll = (current_time) => {
            const elapsed = current_time - start_time;
            const progress = Math.min(elapsed / duration, 1);
            const ease_in_out_quad = (t) => t < 0.5
                ? 2 * t * t
                : -1 + (4 - 2 * t) * t;
            element.scrollTop = scroll_top + (scroll_height - scroll_top) * ease_in_out_quad(progress);

            if (progress < 1) {
                requestAnimationFrame(scroll);
            }
        };

        requestAnimationFrame(scroll);
    } else {
        element.scrollTop = scroll_height;
    }
};
