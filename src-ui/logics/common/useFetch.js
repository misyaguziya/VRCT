import { fetch as tauriFetch } from "@tauri-apps/plugin-http";

export const useFetch = () => {
    const asyncTauriFetchGithub = async (url, {return_row = false} = {}) => {
        console.log("tauriFetch", url);

        const response = await tauriFetch(url, {
            method: "GET",
            headers: {
                "Accept": "application/vnd.github+json",
                "User-Agent": "VRCTPluginApp"
            }
        });

        if (response.status !== 200) {
            throw new Error(`Failed to fetch ${url}, response status: ${response.status}`);
        }

        if (return_row === true) return await response;

        return await response.json();
    };

    return {
        asyncTauriFetchGithub,
    };
};