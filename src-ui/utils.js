export const arrayToObject = (array) => {
    return array.reduce((obj, item) => {
        obj[item] = item;
        return obj;
    }, {});
};

export const chunkArray = (array, size) => {
    const chunked = [];
    for (let i = 0; i < array.length; i += size) {
        chunked.push(array.slice(i, i + size));
    }
    return chunked;
};

export const clampMinMax = (value, min, max) => {
    return Math.min(Math.max(value, min), max);
};
// console.log(clamp(5, 1, 10));  // 5 (範囲内)
// console.log(clamp(-3, 0, 10)); // 0 (minより小さい)
// console.log(clamp(15, 1, 10)); // 10 (maxより大きい)
// console.log(clamp(7.5, 1, 10)); // 7.5 (範囲内、少数)

export const randomIntMinMax = (min, max) => {
	if (min === max) return min;
	if (max === undefined) {
		max = min;
		min = 0;
	}
	const int = Math.floor(Math.random() * (max - min + 1)) + min;
	return int;
};

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

export const updateLabelsById = (data_array, updates) => {
    return data_array.map(item => {
        const update = updates.find(update_item => update_item.id === item.id);
        return update ? { ...item, label: update.label } : item;
    });
};