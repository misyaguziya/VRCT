import { useSelectedConfigTabId } from "@store";

import { Device } from "./device/Device";
import { Appearance } from "./appearance/Appearance";
// import { Others } from "./others/Others";
// import { AboutVrct } from "./about_vrct/AboutVrct";

export const SettingBox = () => {
    const { currentSelectedConfigTabId } = useSelectedConfigTabId();
    switch (currentSelectedConfigTabId) {
        case "device":
            return <Device />;
        // case "others":
        //     return <Others />;
        // case "appearance":
        //     return <Appearance />;
        // case "about_vrct":
        //     return <AboutVrct />;

        default:
            return null;
    }
};