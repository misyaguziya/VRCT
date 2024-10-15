import { useStore_SpeakerRecordTimeout } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSpeakerRecordTimeout = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSpeakerRecordTimeout, updateSpeakerRecordTimeout, pendingSpeakerRecordTimeout } = useStore_SpeakerRecordTimeout();

    const getSpeakerRecordTimeout = () => {
        pendingSpeakerRecordTimeout();
        asyncStdoutToPython("/get/data/speaker_record_timeout");
    };

    const setSpeakerRecordTimeout = (selected_speaker_record_timeout) => {
        pendingSpeakerRecordTimeout();
        asyncStdoutToPython("/set/data/speaker_record_timeout", selected_speaker_record_timeout);
    };

    return {
        currentSpeakerRecordTimeout,
        getSpeakerRecordTimeout,
        updateSpeakerRecordTimeout,
        setSpeakerRecordTimeout,
    };
};