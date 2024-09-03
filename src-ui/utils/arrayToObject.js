export const arrayToObject = (array) => {
    return array.reduce((obj, item) => {
        obj[item] = item;
        return obj;
    }, {});
};