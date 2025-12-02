export const arrayToObject = (array) => {
    return array.reduce((obj, item) => {
        obj[item] = item;
        return obj;
    }, {});
};

export const speakerDeviceArrayToObject = (array) => {
    // Transform speaker device array with type information
    // Input: [{name: "Device1", index: 0, isLoopbackDevice: true}, ...]
    // Output: {"Device1": "Device1 (Loopback)", "Device2": "Device2 (Output)", ...}
    return array.reduce((obj, device) => {
        if (typeof device === 'string') {
            // Fallback for old format (just strings)
            obj[device] = device;
        } else if (device && device.name) {
            const deviceType = device.isLoopbackDevice ? " (Loopback)" : " (Output)";
            const displayName = device.name === "NoDevice" ? device.name : device.name + deviceType;
            obj[device.name] = displayName;
        }
        return obj;
    }, {});
};

export const arrayToIdLabel = (array) => {
    return array.map((element) => ({
        id: element,
        label: element,
    }));
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

export const genNumArray = (count, start_from = 0) => {
    return [...Array(count).keys()].map(i => i + start_from);
};

export const genNumObjArray = (count, start_from = 0) => {
    return arrayToObject(genNumArray(count, start_from));
};

// This is using for only AI models compute device list, currently. (CTranslate2, Whisper)
export const transformToIndexedArray = (devices) => {
    return devices.reduce((result, device, index) => {
        result[index] = device;
        return result;
    }, {});
};