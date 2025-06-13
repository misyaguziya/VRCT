import { useStore_MicRecordTimeout } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useMicRecordTimeout = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicRecordTimeout, updateMicRecordTimeout, pendingMicRecordTimeout } = useStore_MicRecordTimeout();

    const getMicRecordTimeout = () => {
        pendingMicRecordTimeout();
        asyncStdoutToPython("/get/data/mic_record_timeout");
    };

    const setMicRecordTimeout = (selected_mic_record_timeout) => {
        pendingMicRecordTimeout();
        asyncStdoutToPython("/set/data/mic_record_timeout", selected_mic_record_timeout);
    };

    return {
        currentMicRecordTimeout,
        getMicRecordTimeout,
        updateMicRecordTimeout,
        setMicRecordTimeout,
    };
};