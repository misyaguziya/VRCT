import { useStore_EnableNotificationVrcSfx } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useEnableNotificationVrcSfx = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableNotificationVrcSfx, updateEnableNotificationVrcSfx, pendingEnableNotificationVrcSfx } = useStore_EnableNotificationVrcSfx();

    const getEnableNotificationVrcSfx = () => {
        pendingEnableNotificationVrcSfx();
        asyncStdoutToPython("/get/data/notification_vrc_sfx");
    };

    const toggleEnableNotificationVrcSfx = () => {
        pendingEnableNotificationVrcSfx();
        if (currentEnableNotificationVrcSfx.data) {
            asyncStdoutToPython("/set/disable/notification_vrc_sfx");
        } else {
            asyncStdoutToPython("/set/enable/notification_vrc_sfx");
        }
    };

    return {
        currentEnableNotificationVrcSfx,
        getEnableNotificationVrcSfx,
        toggleEnableNotificationVrcSfx,
        updateEnableNotificationVrcSfx,
    };
};