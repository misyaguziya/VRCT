import { useState, useEffect } from "react";

import CircularProgress from '@mui/material/CircularProgress';
import styles from "./SplashComponent.module.scss";

export const SplashComponent = () => {
    const [circular_color, setCircularColor] = useState("");
    useEffect(() => {
        const circular_color = getComputedStyle(document.documentElement).getPropertyValue("--primary_300_color");
        setCircularColor(circular_color.trim());
    }, []);

    return (
        <div>
            <CircularProgress size="14rem" sx={{ color: circular_color }}/>
        </div>
    );
};