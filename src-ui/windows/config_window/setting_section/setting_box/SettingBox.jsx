import styles from "./SettingBox.module.scss";
import { useSelectedConfigTab } from "@store";

import { Appearance } from "./appearance/Appearance";
import { AboutVrct } from "./about_vrct/AboutVrct";

export const SettingBox = () => {
    const { currentSelectedConfigTab } = useSelectedConfigTab();
    switch (currentSelectedConfigTab) {
        case "appearance":
            return <Appearance />;
        case "about_vrct":
            return <AboutVrct />;

        default:
            return null;
    }
};