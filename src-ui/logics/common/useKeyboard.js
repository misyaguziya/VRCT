import { getStoreHook, useStore_KeyboardSendResult } from "@store";
import { useMessage } from "./useMessage";

// VRキーボードの送信の応答 (/run/keyboard_send)。VRCT で送ったものはメインのログにも出す
export const useKeyboard = () => {
    const { updateKeyboardState } = getStoreHook("KeyboardState")();
    const { currentKeyboardSendResult, updateKeyboardSendResult } = useStore_KeyboardSendResult();
    const { addSentMessageLog } = useMessage();

    const receiveKeyboardSend = (result) => {
        updateKeyboardState(result.state);
        // 何も打っていなかった (送っていない)
        if (result.message === undefined && result.pasted === undefined) return;
        if (result.message) addSentMessageLog(result.message);
        updateKeyboardSendResult({ to: result.to, pasted: result.pasted ?? null, at: Date.now() });
    };

    return { receiveKeyboardSend, currentKeyboardSendResult };
};
