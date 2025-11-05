import {
    RadioButton,
} from "../index";
import { _DownloadButton } from "../_atoms/_download_button/_DownloadButton";

export const DownloadModels = (props) => {
    const options = props.options.map(item => ({
        ...item,
        disabled: !item.is_downloaded
    }));

    return (
        <>
            <RadioButton
                selectFunction={props.selectFunction}
                name={props.name}
                options={options}
                checked_variable={props.checked_variable}
                column={true}
                ChildComponent={_DownloadButton}
                downloadStartFunction={props.downloadStartFunction}
            />
        </>
    );
};