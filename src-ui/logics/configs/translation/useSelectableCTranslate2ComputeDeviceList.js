import { useStore_SelectableCTranslate2ComputeDeviceList } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { transformToIndexedArray } from "@utils";

export const useSelectableCTranslate2ComputeDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectableCTranslate2ComputeDeviceList, updateSelectableCTranslate2ComputeDeviceList, pendingSelectableCTranslate2ComputeDeviceList } = useStore_SelectableCTranslate2ComputeDeviceList();

    const getSelectableCTranslate2ComputeDeviceList = () => {
        pendingSelectableCTranslate2ComputeDeviceList();
        asyncStdoutToPython("/get/data/translation_compute_device_list");
    };

    const updateSelectableCTranslate2ComputeDeviceList_FromBackend = (payload) => {
        updateSelectableCTranslate2ComputeDeviceList(transformToIndexedArray(payload));
    };

    return {
        currentSelectableCTranslate2ComputeDeviceList,
        getSelectableCTranslate2ComputeDeviceList,
        updateSelectableCTranslate2ComputeDeviceList,

        updateSelectableCTranslate2ComputeDeviceList_FromBackend,
    };
};