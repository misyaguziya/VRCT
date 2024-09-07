import {
    useMicVolume,
} from "@store";

import { useStdoutToPython } from "./useStdoutToPython";


export const useVolume = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateMicVolume } = useMicVolume();

    // const asyncPending = () => new Promise(() => {});
    return {
        volumeCheckStart_Mic: () => asyncStdoutToPython("/controller/callback_enable_check_mic_threshold"),
        volumeCheckStop_Mic: () => asyncStdoutToPython("/controller/callback_disable_check_mic_threshold"),
        updateVolumeVariable_Mic: (payload) => {
            updateMicVolume(payload.data);
        }


    };
};