import React, { useState, useEffect } from "react";
import styles from "./Slider.module.scss";
import MUI_Slider from "@mui/material/Slider";

export const Slider = (props) => {
    const [baseColor, setBaseColor] = useState("");
    const [activeColor, setActiveColor] = useState("");
    const [toolTipColor, setToolTipColor] = useState("");

    useEffect(() => {
        const baseColor = getComputedStyle(document.documentElement).getPropertyValue("--dark_700_color");
        setBaseColor(baseColor.trim());
        const activeColor = getComputedStyle(document.documentElement).getPropertyValue("--primary_600_color");
        setActiveColor(activeColor.trim());
        const toolTipColor = getComputedStyle(document.documentElement).getPropertyValue("--dark_800_color");
        setToolTipColor(toolTipColor.trim());
    }, []);

    return (
        <div className={styles.container}>
            <MUI_Slider
                className={styles.range_slider}
                defaultValue={50}
                aria-label="Default"
                valueLabelDisplay="auto"
                value={props.variable}
                step={props.step}
                min={Number(props.min)}
                max={Number(props.max)}
                onChange={(_e, value) => props.onchangeFunction(value)}
                onChangeCommitted={(_e, value) => props.onchangeCommittedFunction(value)}
                marks={props.marks}
                track={props.track}
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
                        "& .MuiSlider-markLabel": {
                            fontSize: "1.4rem",
                            color: "white"
                        },
                        "& .MuiSlider-markLabelActive": {
                            color: activeColor,
                        }
                    }}
            />
        </div>
    );
};
