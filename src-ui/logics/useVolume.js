import {
    useStore_MicVolume,
    useStore_SpeakerVolume,
    useStore_MicThresholdCheckStatus,
    useStore_SpeakerThresholdCheckStatus,
} from "@store";

import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useVolume = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateMicVolume } = useStore_MicVolume();
    const { updateSpeakerVolume } = useStore_SpeakerVolume();
    const { currentMicThresholdCheckStatus, updateMicThresholdCheckStatus } = useStore_MicThresholdCheckStatus();
    const { currentSpeakerThresholdCheckStatus, updateSpeakerThresholdCheckStatus } = useStore_SpeakerThresholdCheckStatus();

    const asyncPending = () => new Promise(() => {});
    return {
        volumeCheckStart_Mic: () => {
            updateMicThresholdCheckStatus(asyncPending);
            asyncStdoutToPython("/controller/callback_enable_check_mic_threshold");
        },
        volumeCheckStop_Mic: () => {
            updateMicThresholdCheckStatus(asyncPending);
            asyncStdoutToPython("/controller/callback_disable_check_mic_threshold");
        },
        updateVolumeVariable_Mic: (payload) => {
            updateMicVolume(payload);
        },
        currentMicThresholdCheckStatus: currentMicThresholdCheckStatus,
        updateMicThresholdCheckStatus: (payload) => {
            updateMicThresholdCheckStatus(payload);
            if (payload === false) updateMicVolume("0");
        },

        volumeCheckStart_Speaker: () => {
            updateSpeakerVolume("0");
            updateSpeakerThresholdCheckStatus(asyncPending);
            asyncStdoutToPython("/controller/callback_enable_check_speaker_threshold");
        },
        volumeCheckStop_Speaker: () => {
            updateSpeakerThresholdCheckStatus(asyncPending);
            asyncStdoutToPython("/controller/callback_disable_check_speaker_threshold");
        },
        updateVolumeVariable_Speaker: (payload) => {
            updateSpeakerVolume(payload);
        },
        currentSpeakerThresholdCheckStatus: currentSpeakerThresholdCheckStatus,
        updateSpeakerThresholdCheckStatus: (payload) => {
            updateSpeakerThresholdCheckStatus(payload);
            if (payload === false) updateSpeakerVolume("0");
        }

    };
};