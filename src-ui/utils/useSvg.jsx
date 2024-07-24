import React from "react";

export const useSvg = (svg_component, ...props) => {
    const svgWithClass = svg_component
        ? React.cloneElement(svg_component, ...props)
        : null;

    return svgWithClass;
};