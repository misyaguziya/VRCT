import { useStore_SpeakerPhraseTimeout } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSpeakerPhraseTimeout = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSpeakerPhraseTimeout, updateSpeakerPhraseTimeout, pendingSpeakerPhraseTimeout } = useStore_SpeakerPhraseTimeout();

    const getSpeakerPhraseTimeout = () => {
        pendingSpeakerPhraseTimeout();
        asyncStdoutToPython("/get/data/speaker_phrase_timeout");
    };

    const setSpeakerPhraseTimeout = (selected_speaker_phrase_timeout) => {
        pendingSpeakerPhraseTimeout();
        asyncStdoutToPython("/set/data/speaker_phrase_timeout", selected_speaker_phrase_timeout);
    };

    return {
        currentSpeakerPhraseTimeout,
        getSpeakerPhraseTimeout,
        updateSpeakerPhraseTimeout,
        setSpeakerPhraseTimeout,
    };
};