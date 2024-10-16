import { useStore_SelectedConfigTabId } from "@store";

import { Device } from "./device/Device";
import { Appearance } from "./appearance/Appearance";
import { Transcription } from "./transcription/Transcription";
import { Others } from "./others/Others";
// import { AboutVrct } from "./about_vrct/AboutVrct";

export const SettingBox = () => {
    const { currentSelectedConfigTabId } = useStore_SelectedConfigTabId();
    switch (currentSelectedConfigTabId.data) {
        case "device":
            return <Device />;
        case "appearance":
            return <Appearance />;
        case "transcription":
            return <Transcription />;
        case "others":
            return <Others />;
        // case "about_vrct":
        //     return <AboutVrct />;

        default:
            return null;
    }
};