import styles from "./HotkeysEntry.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import { useState, useRef } from "react";

export const HotkeysEntry = (props) => {
    const [is_accepting_input, setIsAcceptingInput] = useState(false); // キー入力受付中かどうか
    const lastKeyRef = useRef(null); // 直前のキーを保持
    const [displayValue, setDisplayValue] = useState(props.value[props.hotkey_id]); // 表示用の値
    const isModifierOnlyRef = useRef(false); // 修飾キー単体かどうかのフラグ
    const entryRef = useRef(null);

    const pressedKeys = useRef(new Set()); // 押されているキーを追跡
    const keysRef = useRef([]); // 最新のkeysを保存

    const setHotkeys = (keys) => {
        entryRef.current.blur();
        props.setHotkeys({ [props.hotkey_id]: keys });
    };

    const handleKeyInput = (event) => {
        const keys = [];
        const nonModifierKeys = []; // 修飾キー以外を追跡する配列

        // 修飾キーを判定して追加（重複防止）
        if (event.ctrlKey && !keys.includes("Ctrl")) keys.push("Ctrl");
        if (event.shiftKey && !keys.includes("Shift")) keys.push("Shift");
        if (event.altKey && !keys.includes("Alt")) keys.push("Alt");
        if (event.metaKey && !keys.includes("Super")) keys.push("Super");

        let register_key = event.key === "Meta" ? "Super" : event.key;
        // アルファベットの場合は大文字に変換
        if (/^[a-zA-Z]$/.test(register_key)) {
            register_key = register_key.toUpperCase();
        }

        // 修飾キー以外を追加
        if (!["Control", "Shift", "Alt", "Meta"].includes(event.key)) {
            keys.push(register_key);
            nonModifierKeys.push(register_key); // 修飾キー以外のキーを追跡
        }

        // キーが既に追跡されていない場合のみ追加
        if (!pressedKeys.current.has(register_key)) {
            pressedKeys.current.add(register_key);
        }

        // 最新のキー構成を保存
        keysRef.current = [...keys];

        // 表示用の値を更新
        setDisplayValue(keys.join(" + "));

        // 修飾キー単体かどうかを更新
        isModifierOnlyRef.current = nonModifierKeys.length === 0;

        // 修飾キーのみの場合は登録処理をスキップ
        if (isModifierOnlyRef.current) return;
    };

    const handleKeyDown = (event) => {
        event.preventDefault(); // デフォルト動作を防ぐ

        // 直前のキーと同じならスキップ
        const currentKey = event.key;
        if (lastKeyRef.current === currentKey) {
            return;
        }

        lastKeyRef.current = currentKey; // 今回のキーを記録
        handleKeyInput(event);
    };

    const handleKeyUp = (event) => {
        lastKeyRef.current = null; // キーが離されたらリセット

        // 修飾キーのみの場合でも表示は維持
        if (isModifierOnlyRef.current) {
            setDisplayValue(""); // 非修飾キーが含まれていた場合リセット
        }

        let register_key = event.key === "Meta" ? "Super" : event.key;
        // アルファベットの場合は大文字に変換
        if (/^[a-zA-Z]$/.test(register_key)) {
            register_key = register_key.toUpperCase();
        }
        // 押されているキーから削除
        pressedKeys.current.delete(register_key);

        // 全てのキーが放された場合
        if (pressedKeys.current.size === 0) {

            // 修飾キーのみの場合はスキップ
            const hasNonModifierKeys = keysRef.current.some(
                (key) => !["Ctrl", "Shift", "Alt", "Super"].includes(key)
            );
            if (!hasNonModifierKeys) {
                return;
            }

            // 保存されたキー構成を使用して登録
            setHotkeys(keysRef.current);
        }
    };


    const handleBlur = () => {
        setIsAcceptingInput(false);
        pressedKeys.current.clear();
    };

    return (
        <div className={styles.container}>
            <_Entry
                ref={entryRef}
                type="text"
                placeholder="Press hotkeys keys"
                onFocus={() => [setIsAcceptingInput(true)]}
                onBlur={handleBlur}
                onKeyDown={handleKeyDown}
                onKeyUp={handleKeyUp}
                value={displayValue} // 表示用の値を設定
                width="20rem"
                is_activated={is_accepting_input}
                readOnly
            />
            <button
                className={styles.delete_button}
                onClick={() => [setHotkeys(null), setDisplayValue("")]}
            >
                Delete
            </button>
        </div>
    );
};
