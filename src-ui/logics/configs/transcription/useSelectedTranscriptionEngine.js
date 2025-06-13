import { useStore_SelectedTranscriptionEngine } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useSelectedTranscriptionEngine = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedTranscriptionEngine, updateSelectedTranscriptionEngine, pendingSelectedTranscriptionEngine } = useStore_SelectedTranscriptionEngine();

    const getSelectedTranscriptionEngine = () => {
        pendingSelectedTranscriptionEngine();
        asyncStdoutToPython("/get/data/selected_transcription_engine");
    };

    const setSelectedTranscriptionEngine = (selected_transcription_engine) => {
        pendingSelectedTranscriptionEngine();
        asyncStdoutToPython("/set/data/selected_transcription_engine", selected_transcription_engine);
    };

    return {
        currentSelectedTranscriptionEngine,
        getSelectedTranscriptionEngine,
        updateSelectedTranscriptionEngine,
        setSelectedTranscriptionEngine,
    };
};