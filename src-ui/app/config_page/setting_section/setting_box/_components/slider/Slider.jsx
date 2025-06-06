import React from "react";
import styles from "./Slider.module.scss";
import MUI_Slider from "@mui/material/Slider";
import clsx from "clsx";

export const Slider = (props) => {
    const location = props.valueLabelDisplayLocation || "top";

    const sliderSx = {
        color: "var(--dark_700_color)",
        "& .MuiSlider-thumb": {
            backgroundColor: "var(--primary_600_color)",
            "&:hover, &.Mui-focusVisible, &.Mui-active": {
                boxShadow: `0 0 0 0.8rem var(--primary_600_color_44)`,
            },
            "& .MuiSlider-valueLabel": {
                position: "absolute",
                backgroundColor: "var(--dark_800_color)",
                width: "fit-content",
                minWidth: "4.8rem",
                padding: "0.4rem 0.8rem",
                lineHeight: "1.15",
                "& .MuiSlider-valueLabelLabel": {
                    fontSize: "1.4rem",
                },
                ...(location === "top" && {
                    top: "-110%",
                    left: "50%",
                    transform: "translate(-50%, -50%) scale(0)",
                    transformOrigin: "bottom center",
                    "&.MuiSlider-valueLabelOpen": {
                        transform: "translate(-50%, -50%) scale(1)",
                    },
                    "&::before": {
                        bottom: "0%",
                        left: "50%",
                    },
                }),
                ...(location === "right" && {
                    top: "50%",
                    left: "150%",
                    transform: "translate(0, -50%) scale(0)",
                    transformOrigin: "left center",
                    "&.MuiSlider-valueLabelOpen": {
                        transform: "translate(0, -50%) scale(1)",
                    },
                    "&::before": {
                        bottom: "50%",
                        left: "0",
                    },
                }),
                ...(location === "left" && {
                    // top: "50%",
                    // right: "50%",
                    // transform: "translate(-50%, -50%) scale(0)",
                    // transformOrigin: "bottom center",
                    // "&.MuiSlider-valueLabelOpen": {
                    //     transform: "translate(-50%, -50%) scale(1)",
                    // },
                    // "&::before": {
                    //     bottom: "50%",
                    //     left: "100%",
                    // },
                }),
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
    };

    return (
        <div
            className={clsx(
                styles.container,
                props.className,
                { [styles.no_padding]: props.no_padding || props.is_break_point }
            )}
        >
            <MUI_Slider
                aria-label="Default"
                // valueLabelDisplay="on"
                valueLabelDisplay={props.valueLabelDisplay ? props.valueLabelDisplay : "auto"}
                value={props.variable}
                step={props.step}
                min={Number(props.min)}
                max={Number(props.max)}
                onChange={(_e, value) => props.onchangeFunction(value)}
                onChangeCommitted={(_e, value) =>
                    props.onchangeCommittedFunction ? props.onchangeCommittedFunction(value) : null
                }
                onMouseEnter={(event) =>
                    props.onMouseEnterFunction ? props.onMouseEnterFunction(event) : null
                }
                onMouseLeave={(event) =>
                    props.onMouseLeaveFunction ? props.onMouseLeaveFunction(event) : null
                }
                marks={props.marks}
                track={props.track}
                orientation={props.orientation}
                valueLabelFormat={`${props.valueLabelFormat ? props.valueLabelFormat : props.variable}`}
                sx={sliderSx}
            />
        </div>
    );
};
