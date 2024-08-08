import {
    useSoftwareVersion,
} from "@store";

import { useStdoutToPython } from "./useStdoutToPython";

export const useConfig = () => {
    const {
        updateSoftwareVersion,
    } = useSoftwareVersion();

    const { asyncStdoutToPython } = useStdoutToPython();

    return {
        getSoftwareVersion: () => {
            asyncStdoutToPython({endpoint: "/config/version"});
        },
        updateSoftwareVersion: (payload) => {
            updateSoftwareVersion(payload.data);
        },
    };
};