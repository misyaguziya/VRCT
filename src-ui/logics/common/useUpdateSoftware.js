import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useUpdateSoftware = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const updateSoftware = () => {
        asyncStdoutToPython("/run/update_software");
    };

    return {
        updateSoftware,
    };
};