import { store } from "@store";
import { useStore_MessageInputBoxRatio } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { clampMinMax } from "@utils";
export const useMessageInputBoxRatio = () => {
    const appWindow = store.appWindow;

    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMessageInputBoxRatio, updateMessageInputBoxRatio } = useStore_MessageInputBoxRatio();

    const getMessageInputBoxRatio = () => {
        asyncStdoutToPython("/get/data/message_box_ratio");
    };

    const asyncSetMessageInputBoxRatio = async (ratio) => {
        const minimized = await appWindow.isMinimized();
        if (minimized === true) return; // don't save while the window is minimized.
        const parsed = parseFloat(ratio.toFixed(2));
        const valid_ratio = clampMinMax(parsed, 1, 99);
        asyncStdoutToPython("/set/data/message_box_ratio", valid_ratio);
    };

    return {
        currentMessageInputBoxRatio,
        getMessageInputBoxRatio,
        updateMessageInputBoxRatio,
        asyncSetMessageInputBoxRatio,
    };
};