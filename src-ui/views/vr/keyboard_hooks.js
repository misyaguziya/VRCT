import { useEffect, useRef, useState } from "react";
import { createKeyRepeat } from "./key_repeat";

// キーボードの押し方: 長押しのくり返し、Shift・Ctrl の1回押しとロック、2回押しで実行、印字の動き
// Shift をこの間に2回押すとロック
const SHIFT_LOCK_MS = 400;

// 押している間くり返す (←・◀ ▶)。離す・外れるで止まる
export const useRepeat = () => {
    const repeat = useRef(null);
    if (repeat.current === null) repeat.current = createKeyRepeat();
    const { stop } = repeat.current;
    // (離したことはオーバーレイが必ず送る。窓が切り替わったときも止める)
    useEffect(() => {
        window.addEventListener("mouseup", stop);
        window.addEventListener("blur", stop);
        return () => { stop(); window.removeEventListener("mouseup", stop); window.removeEventListener("blur", stop); };
    }, []);
    return repeat.current;
};

// Shift: 1回押すと次の1文字だけ ("once")、素早く2回でロック ("lock")。ロック中・次の1文字を待っている間に
// もう1回で解除。左右は同じ状態
export const useShift = () => {
    const [shift, setShift] = useState("off");
    const pressed_at = useRef(0);
    const press = () => {
        const now = Date.now();
        const quick = now - pressed_at.current < SHIFT_LOCK_MS;
        pressed_at.current = now;
        setShift(s => (s === "off" ? "once" : s === "once" && quick ? "lock" : "off"));
    };
    // 1文字打った: 1回押しの Shift はそこで外れる
    const used = () => {
        if (shift === "once") setShift("off");
    };
    // Caps Lock: 1回でロック、もう1回で解除
    const toggleLock = () => setShift(s => (s === "lock" ? "off" : "lock"));
    return { shift, is_shift: shift !== "off", press, used, toggleLock };
};

// 2回押しで実行するもの (全消去): 1回目で構え (armed)、within_ms の間にもう1回で実行。間があけば戻る
// (VR で間違えて押しても消えない)
export const useConfirm = (action, within_ms) => {
    const [armed, setArmed] = useState(false);
    useEffect(() => {
        if (!armed) return undefined;
        const timer = setTimeout(() => setArmed(false), within_ms);
        return () => clearTimeout(timer);
    }, [armed, within_ms]);
    const press = () => {
        if (!armed) return setArmed(true);
        setArmed(false);
        action();
    };
    return { armed, press };
};

// 印字が変わるときの動き: Shift のオン・オフ ("shift_on" / "shift_off")、言語の切り替え ("language")。
// 動くのは字が変わったキーだけ (変わった字は作り直され、その時の動きで現れる: Legend)。
// 入力は押した瞬間に変わっていて、見た目だけが追いつく
export const useLegendMotion = (is_shift, language) => {
    const motion = useRef({ is_shift, language, kind: null });
    if (motion.current.language !== language) motion.current = { is_shift, language, kind: "language" };
    else if (motion.current.is_shift !== is_shift) motion.current = { is_shift, language, kind: is_shift ? "shift_on" : "shift_off" };
    return motion.current.kind;
};
