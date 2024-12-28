import styles from "./SplashComponent.module.scss";
import { StartUpProgressContainer } from "./start_up_progress_container/StartUpProgressContainer/";
import { DownloadModelsContainer } from "./download_models_container/DownloadModelsContainer/";

export const SplashComponent = () => {
    return (
        <div>
            <StartUpProgressContainer />
            <DownloadModelsContainer />
        </div>
    );
};