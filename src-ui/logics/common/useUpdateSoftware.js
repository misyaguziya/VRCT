import { useStdoutToPython } from "@useStdoutToPython";

export const useUpdateSoftware = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    // edition は NSIS インストーラの /EDITION= に渡る値 ("cpu" | "gpu")。
    // CPU版/GPU版で別エンドポイントに分かれていたのを1本にまとめた。
    const updateSoftware = (target_version, edition = "cpu") => {
        asyncStdoutToPython("/run/update_software", {
            version: target_version ?? null,
            edition: edition,
        });
    };

    return {
        updateSoftware,
    };
};
