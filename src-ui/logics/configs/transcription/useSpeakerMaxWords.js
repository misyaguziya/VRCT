import { useStore_SpeakerMaxWords } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useSpeakerMaxWords = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSpeakerMaxWords, updateSpeakerMaxWords, pendingSpeakerMaxWords } = useStore_SpeakerMaxWords();

    const getSpeakerMaxWords = () => {
        pendingSpeakerMaxWords();
        asyncStdoutToPython("/get/data/speaker_max_phrases");
    };

    const setSpeakerMaxWords = (selected_speaker_max_phrases) => {
        pendingSpeakerMaxWords();
        asyncStdoutToPython("/set/data/speaker_max_phrases", selected_speaker_max_phrases);
    };

    return {
        currentSpeakerMaxWords,
        getSpeakerMaxWords,
        updateSpeakerMaxWords,
        setSpeakerMaxWords,
    };
};