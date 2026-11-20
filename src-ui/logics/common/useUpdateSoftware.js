import { useStdoutToPython } from "@useStdoutToPython";

// 更新先の版ごとの endpoint。ここにない版は送らない
export const UPDATE_SOFTWARE_ENDPOINTS = {
    cpu: "/run/update_software",
    cuda: "/run/update_cuda_software",
    amd: "/run/update_amd_software",
};

export const useUpdateSoftware = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    // target_version を省略すると最新版
    const updateSoftware = (edition, target_version) => {
        const endpoint = Object.hasOwn(UPDATE_SOFTWARE_ENDPOINTS, edition) ? UPDATE_SOFTWARE_ENDPOINTS[edition] : null;
        if (!endpoint) return false;
        asyncStdoutToPython(endpoint, target_version);
        return true;
    };

    return { updateSoftware };
};