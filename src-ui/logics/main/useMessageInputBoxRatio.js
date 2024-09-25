import { useStore_MessageInputBoxRatio } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";
import { clampMinMax } from "@utils/clampMinMax";
export const useMessageInputBoxRatio = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMessageInputBoxRatio, updateMessageInputBoxRatio } = useStore_MessageInputBoxRatio();

    const getMessageInputBoxRatio = () => {
        asyncStdoutToPython("/get/data/message_box_ratio");
    };

    const setMessageInputBoxRatio = (ratio) => {
        const parsed = parseFloat(ratio.toFixed(2));
        const valid_ratio = clampMinMax(parsed, 1, 99);
        asyncStdoutToPython("/set/data/message_box_ratio", valid_ratio);
    };

    return {
        currentMessageInputBoxRatio,
        getMessageInputBoxRatio,
        updateMessageInputBoxRatio,
        setMessageInputBoxRatio,
    };
};