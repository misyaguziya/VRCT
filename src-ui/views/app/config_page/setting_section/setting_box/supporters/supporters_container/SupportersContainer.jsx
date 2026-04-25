import styles from "./SupportersContainer.module.scss";
import { SupportersWrapper } from "./supporters_wrapper/SupportersWrapper";
import { useSupporters } from "@logics_configs";
import { supporters_images_url } from "@ui_configs";
import vrct_supporters_title from "@images/supporters/vrct_supporters_title.png";

export const SupportersContainer = () => {
    const { currentSupportersData } = useSupporters();

    if (currentSupportersData.state === "error")
        return <div>Failed to retrieve data.</div>;

    if (currentSupportersData.state === "pending" || currentSupportersData.data === null)
        return <div>Loading...</div>;

    const supporters_settings = currentSupportersData.data.supporters_settings;
    const last_updated_local_date = new Date(supporters_settings.last_updated_utc_date).toLocaleString();

    return (
        <div className={styles.supporters_container}>
            <div className={styles.vrct_supporters_title_wrapper}>
                <img className={styles.vrct_supporters_title} src={vrct_supporters_title}/>
                <img className={styles.calc_period} src={`${supporters_images_url}/calc_period_label.png`}/>
                <p className={styles.last_updated_local_date}>{`Last updated date: ${last_updated_local_date}`}</p>
            </div>
            <SupportersWrapper />
            <p className={styles.vrct_supporters_desc_end}>{`みなさんのおかげで、みしゃ社長は布団で寝ることを許され(in開発室) しいなは喜び庭駆け回っています！！！ふわもちもぐもぐです！ありがとうございます。これからもまだまだ進化するVRCTをどうかよろしくお願いします！\nThanks to everyone, Misha has been granted the privilege of sleeping in a proper bed (in the development room), and Shiina is so happy, running around the yard! Fuwa-mochi-mogu-mogu! Thank you so much! We hope you'll continue to support the ever-evolving VRCT!`}</p>
        </div>
    );
};