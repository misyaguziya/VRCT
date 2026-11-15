// 長押しの反復。最初の1回は即時、500msの待機後に80ms間隔で実行する。
export const createKeyRepeat = () => {
    let timer = null;
    const stop = () => {
        clearTimeout(timer);
        clearInterval(timer);
        timer = null;
    };
    const start = (action) => {
        stop();
        action();
        timer = setTimeout(() => { timer = setInterval(action, 80); }, 500);
    };
    return { start, stop };
};
