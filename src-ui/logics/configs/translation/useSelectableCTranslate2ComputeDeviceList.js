import { useStore_SelectableCTranslate2ComputeDeviceList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectableCTranslate2ComputeDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectableCTranslate2ComputeDeviceList, updateSelectableCTranslate2ComputeDeviceList, pendingSelectableCTranslate2ComputeDeviceList } = useStore_SelectableCTranslate2ComputeDeviceList();

    const getSelectableCTranslate2ComputeDeviceList = () => {
        pendingSelectableCTranslate2ComputeDeviceList();
        asyncStdoutToPython("/get/data/translation_compute_device_list");
    };

    return {
        currentSelectableCTranslate2ComputeDeviceList,
        getSelectableCTranslate2ComputeDeviceList,
        updateSelectableCTranslate2ComputeDeviceList,
    };
};