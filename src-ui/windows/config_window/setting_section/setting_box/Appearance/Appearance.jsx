import { useSettingBox } from "../useSettingBox";
import { useSelectedMicDevice, useMicDeviceList } from "@store";
export const Appearance = () => {
    const { currentSelectedMicDevice, updateSelectedMicDevice } = useSelectedMicDevice();
    const { currentMicDeviceList } = useMicDeviceList();
    const { DropdownMenuContainer } = useSettingBox();

    const selectFunction = (selected_data) => {
        const asyncFunction = () => {
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve(selected_data.selected_id);
                }, 3000);
            });
        };
        updateSelectedMicDevice(asyncFunction);
    };

    return (
        <>
            <DropdownMenuContainer dropdown_id="mic_host" label="Mic Host/Driver" desc="description" selected_id="b" list={{a: "A", b: "B", c: "C"}} />
            <DropdownMenuContainer dropdown_id="mic_device" label="Mic Device" desc="description" selected_id={currentSelectedMicDevice.data} list={currentMicDeviceList} selectFunction={selectFunction} state={currentSelectedMicDevice.state} />
        </>
    );
};