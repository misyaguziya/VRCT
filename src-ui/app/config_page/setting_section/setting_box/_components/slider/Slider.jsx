import React from "react";
import styles from "./Slider.module.scss";
import MUI_Slider from "@mui/material/Slider";
import { clsx } from "clsx";

export const Slider = (props) => {
    return (
        <div className={clsx(styles.container, props.className, {[styles.no_padding]: props.no_padding || props.is_break_point})}>
            <MUI_Slider
                aria-label="Default"
                valueLabelDisplay="auto"
                value={props.variable}
                step={props.step}
                min={Number(props.min)}
                max={Number(props.max)}
                onChange={(_e, value) => props.onchangeFunction(value)}
                onChangeCommitted={(_e, value) => props.onchangeCommittedFunction ? props.onchangeCommittedFunction(value) : null}
                marks={props.marks}
                track={props.track}
                orientation={props.orientation}
                valueLabelFormat={`${props.valueLabelFormat ? props.valueLabelFormat : props.variable}`}
                sx={{
                    color: "var(--dark_700_color)",
                    "& .MuiSlider-thumb": {
                        backgroundColor: "var(--primary_600_color)",
                        "&:hover, &.Mui-focusVisible, &.Mui-active": {
                            boxShadow: `0 0 0 0.8rem var(--primary_600_color_44)`,
                        },
                        "& .MuiSlider-valueLabel": {
                            fontSize: "1.4rem",
                            backgroundColor: "var(--dark_800_color)",
                            padding: "0.6rem 1rem",
                            lineHeight: "1.15",
                            // top: "-1.4rem",
                            // "&::before": {
                            //     left: "30%",
                            //     width: "1rem",
                            //     height: "1rem",
                            //     clipPath: "polygon(50% 0, 100% 100%, 0 100%)",
                            // },
                        },
                    },
                    "& .MuiSlider-markLabel": {
                        fontSize: "1.4rem",
                        color: "var(--dark_550_color)",
                        whiteSpace: "nowrap",
                    },
                    "& .MuiSlider-markLabelActive": {
                        color: "var(--primary_300_color)",
                    },
                }}
            />
        </div>
    );
};
