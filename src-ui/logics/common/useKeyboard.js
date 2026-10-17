import { getStoreHook, useStore_KeyboardSendResult } from "@store";
import { useMessage } from "./useMessage";

// VRキーボードで Enter を押して送った結果 (/run/keyboard_sent)。VRCT で送ったものはメインのログにも出す
export const useKeyboard = () => {
    const { updateKeyboardState } = getStoreHook("KeyboardState")();
    const { currentKeyboardSendResult, updateKeyboardSendResult } = useStore_KeyboardSendResult();
    const { addSentMessageLog } = useMessage();

    const receiveKeyboardSend = (result) => {
        updateKeyboardState(result.state);
        if (result.message) addSentMessageLog(result.message);
        updateKeyboardSendResult({ to: result.to, pasted: result.pasted ?? null, at: Date.now() });
    };

    return { receiveKeyboardSend, currentKeyboardSendResult };
};
