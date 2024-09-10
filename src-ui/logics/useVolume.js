import {
    useStore_MicVolume,
    useStore_SpeakerVolume,
} from "@store";

import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useVolume = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateMicVolume } = useStore_MicVolume();
    const { updateSpeakerVolume } = useStore_SpeakerVolume();

    return {
        volumeCheckStart_Mic: () => asyncStdoutToPython("/controller/callback_enable_check_mic_threshold"),
        volumeCheckStop_Mic: () => asyncStdoutToPython("/controller/callback_disable_check_mic_threshold"),
        updateVolumeVariable_Mic: (payload) => {
            updateMicVolume(payload);
        },

        volumeCheckStart_Speaker: () => asyncStdoutToPython("/controller/callback_enable_check_speaker_threshold"),
        volumeCheckStop_Speaker: () => asyncStdoutToPython("/controller/callback_disable_check_speaker_threshold"),
        updateVolumeVariable_Speaker: (payload) => {
            updateSpeakerVolume(payload);
        },

    };
};