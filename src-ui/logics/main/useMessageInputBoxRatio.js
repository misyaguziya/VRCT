import { useStore_MessageInputBoxRatio } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMessageInputBoxRatio = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMessageInputBoxRatio, updateMessageInputBoxRatio } = useStore_MessageInputBoxRatio();

    const getMessageInputBoxRatio = () => {
        asyncStdoutToPython("/get/data/message_box_ratio");
    };

    const setMessageInputBoxRatio = (ratio) => {
        asyncStdoutToPython("/set/data/message_box_ratio", parseFloat(ratio.toFixed(2)));
    };

    return {
        currentMessageInputBoxRatio,
        getMessageInputBoxRatio,
        updateMessageInputBoxRatio,
        setMessageInputBoxRatio,
    };
};