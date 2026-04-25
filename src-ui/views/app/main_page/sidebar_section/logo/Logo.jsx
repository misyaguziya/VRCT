import styles from "./Logo.module.scss";

export const Logo = () => {
    return (
        <div className={styles.container}>
            <LogoBox />
        </div>
    );
};


import vrct_logo from "@images/vrct_logo_for_dark_mode.png";
import chato_img from "@images/chato_white.png";
import { useIsMainPageCompactMode } from "@logics_main";

export const LogoBox = () => {
    const { currentIsMainPageCompactMode } = useIsMainPageCompactMode();
    if (currentIsMainPageCompactMode.data === true) {
        return <img src={chato_img} className={styles.logo_chato} alt="VRCT logo chato" />;
    } else {
        return <img src={vrct_logo} className={styles.logo} alt="VRCT logo" />;
    }
};