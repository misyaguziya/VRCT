import { useSettingBox } from "../components/useSettingBox";
import { useSelectedMicDeviceStatus, useMicDeviceListStatus } from "@store";
export const Appearance = () => {
    const { currentSelectedMicDeviceStatus, updateSelectedMicDeviceStatus } = useSelectedMicDeviceStatus();
    const { currentMicDeviceListStatus } = useMicDeviceListStatus();
    const {
        DropdownMenuContainer,
        SliderContainer,
        CheckboxContainer,
        SwitchboxContainer,
    } = useSettingBox();

    const selectFunction = (selected_data) => {
        const asyncFunction = () => {
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve(selected_data.selected_id);
                }, 3000);
            });
        };
        updateSelectedMicDeviceStatus(asyncFunction);
    };

    return (
        <>
            <DropdownMenuContainer dropdown_id="mic_host" label="Mic Host/Driver" desc="description" selected_id="b" list={{a: "A", b: "B", c: "C"}} />
            <DropdownMenuContainer dropdown_id="mic_device" label="Mic Device" desc="description" selected_id={currentSelectedMicDeviceStatus.data} list={currentMicDeviceListStatus} selectFunction={selectFunction} state={currentSelectedMicDeviceStatus.state} />

            <SliderContainer label="Transparent" desc="description" min="0" max="3000"/>
            <CheckboxContainer label="Transparent" desc="description" checkbox_id="checkbox_id_1"/>
            <SwitchboxContainer label="Transparent" desc="description" switchbox_id="switchbox_id_1"/>
        </>
    );
};