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

export const randomMinMax = (min, max) => {
    return Math.random() * (max - min) + min;
};

export const shuffleArray = (array) => {
    const new_array = [...array];
    for (let i = new_array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [new_array[i], new_array[j]] = [new_array[j], new_array[i]];
    }
    return new_array;
};

export const updateLabelsById = (data_array, updates) => {
    return data_array.map(item => {
        const update = updates.find(update_item => update_item.id === item.id);
        return update ? { ...item, label: update.label } : item;
    });
};