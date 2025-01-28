import styles from "./Supporters.module.scss";
import { SupportUsContainer } from "./support_us_container/SupportUsContainer";
import { SupportersContainer } from "./supporters_container/SupportersContainer";

export const Supporters = () => {
    return (
        <div className={styles.container}>
            <SupportUsContainer />
            <SupportersContainer />
        </div>
    );
};