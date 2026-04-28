import styles from "./Supporters.module.scss";
import { SupportUsContainer } from "./support_us_container/SupportUsContainer";
import { SupportersContainer } from "./supporters_container/SupportersContainer";
import { useSupporters } from "@logics_configs";
import { useEffect } from "react";

export const Supporters = () => {
    const { asyncFetchSupportersData } = useSupporters();

    useEffect(() => {
        asyncFetchSupportersData();
    }, []);

    return (
        <div className={styles.container}>
            <SupportUsContainer />
            <div className={styles.supportersWrapper}>
                <SupportersContainer />
            </div>
        </div>
    );
};