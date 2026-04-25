import { useStore_SupportersData } from "@store";
import { supporters_data_url } from "@ui_configs";
export const useSupporters = () => {
    const { currentSupportersData, updateSupportersData, pendingSupportersData, errorSupportersData } = useStore_SupportersData();

    const asyncFetchSupportersData = async () => {
        if (currentSupportersData.state === "pending") return;
        pendingSupportersData();
        try {
            const res = await fetch(supporters_data_url);
            // const res = await fetch(supporters_data_url, { cache: "no-store" });
            if (!res.ok) {
                throw new Error("Network response was not ok");
            }
            const data = await res.json();
            updateSupportersData(data);
        } catch (error) {
            console.error("Error fetching supporters' data:", error);
            errorSupportersData();
        }
    };

    return {
        asyncFetchSupportersData,
        currentSupportersData,
        updateSupportersData,
        pendingSupportersData,
    };
};