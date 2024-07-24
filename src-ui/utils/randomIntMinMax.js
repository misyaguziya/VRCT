export const randomIntMinMax = (min, max) => {
	if (min === max) return min;
	if (max === undefined) {
		max = min;
		min = 0;
	}
	const int = Math.floor(Math.random() * (max - min + 1)) + min;
	return int;
};
