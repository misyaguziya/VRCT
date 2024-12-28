import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useUpdateSoftware = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const updateSoftware = () => {
        asyncStdoutToPython("/run/update_software");
    };

    const updateSoftware_CUDA = () => {
        asyncStdoutToPython("/run/update_cuda_software");
    };

    return {
        updateSoftware,
        updateSoftware_CUDA,
    };
};