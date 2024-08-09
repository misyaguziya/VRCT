import { useSelectedConfigTabId } from "@store";

import { Appearance } from "./appearance/Appearance";
import { AboutVrct } from "./about_vrct/AboutVrct";

export const SettingBox = () => {
    const { currentSelectedConfigTabId } = useSelectedConfigTabId();
    switch (currentSelectedConfigTabId) {
        case "appearance":
            return <Appearance />;
        case "about_vrct":
            return <AboutVrct />;

        default:
            return null;
    }
};