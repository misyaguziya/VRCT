import React, { useState, useEffect } from "react";
import styles from "./Slider.module.scss";
import MUI_Slider from "@mui/material/Slider";

export const Slider = ({ min, max }) => {
    const [baseColor, setBaseColor] = useState("");
    const [activeColor, setActiveColor] = useState("");
    const [toolTipColor, setToolTipColor] = useState("");

    useEffect(() => {
        const baseColor = getComputedStyle(document.documentElement).getPropertyValue("--dark_700_color");
        const activeColor = getComputedStyle(document.documentElement).getPropertyValue("--primary_600_color");
        const toolTipColor = getComputedStyle(document.documentElement).getPropertyValue("--dark_800_color");
        setBaseColor(baseColor.trim());
        setActiveColor(activeColor.trim());
        setToolTipColor(toolTipColor.trim());
    }, []);

    const showSliderValue = (_e, value) => {
        console.log(value);
    };

    return (
        <div className={styles.container}>
        <MUI_Slider className={styles.range_slider} defaultValue={50} aria-label="Default" valueLabelDisplay="auto"
        step={1}
        min={Number(min)}
        max={Number(max)}
        onChange={showSliderValue}
        sx={{
            color: baseColor,
                "& .MuiSlider-thumb": {
                    backgroundColor: activeColor,
                    "&:hover, &.Mui-focusVisible, &.Mui-active": {
                        boxShadow: "0 0 0 0.8rem" + activeColor + "44",
                    },
                    "& .MuiSlider-valueLabel": {
                        fontSize: "1.4rem",
                        backgroundColor: toolTipColor,
                        padding: "0.6rem 1rem",
                        lineHeight: "1.15",
                        top: "-1.4rem",
                        "&::before": {
                            left: "30%",
                            width: "1rem",
                            height: "1rem",
                            clipPath: "polygon(50% 0, 100% 100%, 0 100%)",
                        }
                    }
                },
            }}
        />
        </div>
    );
};
