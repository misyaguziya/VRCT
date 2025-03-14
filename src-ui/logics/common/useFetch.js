import { fetch as tauriFetch, ResponseType } from "@tauri-apps/api/http";

export const useFetch = () => {
    const asyncTauriFetchGithub = async (url) => {
        console.log("tauriFetch", url);

        const release_response = await tauriFetch(url, {
            method: "GET",
            responseType: ResponseType.Json,
            headers: {
                "Accept": "application/vnd.github+json",
                "User-Agent": "VRCTPluginApp"
            }
        });
        return release_response;
    };

    return {
        asyncTauriFetchGithub,
    };
};