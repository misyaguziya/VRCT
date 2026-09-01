import { useStdoutToPython } from "@useStdoutToPython";

export const useUpdateSoftware = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const updateSoftware = (target_version) => {
        asyncStdoutToPython("/run/update_software", target_version);
    };

    const updateSoftware_CUDA = (target_version) => {
        asyncStdoutToPython("/run/update_cuda_software", target_version);
    };

    return {
        updateSoftware,
        updateSoftware_CUDA,
    };
};