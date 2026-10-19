import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { useStdoutToPython } from "@useStdoutToPython";
import { useVr } from "@logics_configs";
import { tooltipGeometry, tooltipMarker } from "../../logics/common/vrPanelTooltip";
import styles from "./VrTooltip.module.scss";

const TARGET = "button[data-tooltip-title]";
const REQUEST = "/run/vr_panel_tooltip";

export const VrTooltipButton = ({ tipTitle, tipState, tipHelp, children, ...props }) => {
    const id = useId();
    return <button {...props} type="button" data-tooltip-title={tipTitle}
        data-tooltip-state={tipState} data-tooltip-help={tipHelp} aria-describedby={id}>
        {children}<span id={id} className={styles.sr_only}>{[tipState, tipHelp].filter(Boolean).join(". ")}</span>
    </button>;
};

// The body lives in an atlas region. Python displays that region in one shared,
// non-interactive overlay above the target, after verifying the captured marker.
export const VrTooltip = ({ atlasRef, layout }) => {
    const [tip, setTip] = useState(null);
    const body = useRef(null);
    const sequence = useRef({ epoch: 0, revision: 0 });
    const send = useRef(null);
    send.current = useStdoutToPython().asyncStdoutToPython;
    const epoch = layout.tooltip_epoch ?? 0;
    const regionKey = JSON.stringify([layout.regions.launcher, layout.regions.toolbar]);
    // 設定でOFFのときは出さない (出ている途中でOFFにすると、下の cleanup が消す)
    const enabled = useVr().currentOverlayVrTooltip.data !== false;

    useEffect(() => {
        const atlas = atlasRef.current;
        if (!atlas || !epoch || !enabled) { setTip(null); return; }
        if (sequence.current.epoch !== epoch) sequence.current = { epoch, revision: 0 };
        let target = null;
        let mode = "hover";
        let dismissed = null;
        let timer = null;
        let snapshot = "";
        let disposed = false;
        let preferFocus = atlas.contains(document.activeElement) && document.activeElement.matches(":focus-visible");
        const next = () => ++sequence.current.revision;
        const transmit = payload => Promise.resolve(send.current(REQUEST, payload)).catch(console.error);
        const hide = () => {
            clearTimeout(timer);
            timer = null;
            setTip(null);
            transmit({ epoch, revision: next(), visible: false });
        };
        const show = () => {
            timer = null;
            if (!target?.isConnected || dismissed === target) return;
            const regionElement = target.closest("[data-vr-region]");
            const region = regionElement?.dataset.vrRegion;
            if (region !== "launcher" && region !== "toolbar") return;
            const [, , width, height] = layout.regions[region];
            const geometry = tooltipGeometry(regionElement.getBoundingClientRect(), target.getBoundingClientRect(), width, height);
            if (!geometry) return;
            setTip({ epoch, revision: next(), visible: true, region, mode, ...geometry,
                title: target.dataset.tooltipTitle, state: target.dataset.tooltipState, help: target.dataset.tooltipHelp });
        };
        const update = (records = []) => {
            if (disposed) return;
            if (records.some(record => record.attributeName === "data-vr-hover")) preferFocus = false;
            const active = atlas.contains(document.activeElement) && document.activeElement.matches(":focus-visible")
                ? document.activeElement.closest(TARGET) : null;
            const hovered = atlas.querySelector(`${TARGET}[data-vr-hover]`);
            const candidate = preferFocus ? active : hovered;
            const nextMode = preferFocus ? "focus" : "hover";
            const content = candidate ? [candidate.dataset.tooltipTitle, candidate.dataset.tooltipState,
                candidate.dataset.tooltipHelp].join("\u0000") : "";
            if (candidate === target && nextMode === mode && content === snapshot) return;
            const isNewTarget = candidate !== target || nextMode !== mode;
            hide();
            if (candidate !== target) dismissed = null;
            target = candidate;
            mode = nextMode;
            snapshot = content;
            if (target && dismissed !== target) {
                timer = setTimeout(show, mode === "focus" || !isNewTarget ? 0 : 300);
            }
        };
        const focus = () => {
            if (document.activeElement.matches(":focus-visible")) preferFocus = true;
            else if (atlas.contains(document.activeElement)) preferFocus = false;
            update();
        };
        const blur = () => queueMicrotask(focus);
        const keydown = event => {
            if (event.key === "Escape") { dismissed = target; hide(); }
            else if (event.key === "Tab") preferFocus = true;
        };
        const observer = new MutationObserver(update);
        observer.observe(atlas, { subtree: true, attributes: true, childList: true,
            attributeFilter: ["data-vr-hover", "data-tooltip-title", "data-tooltip-state", "data-tooltip-help"] });
        atlas.addEventListener("focusin", focus);
        atlas.addEventListener("focusout", blur);
        document.addEventListener("keydown", keydown);
        update();
        return () => {
            disposed = true;
            observer.disconnect();
            atlas.removeEventListener("focusin", focus);
            atlas.removeEventListener("focusout", blur);
            document.removeEventListener("keydown", keydown);
            hide();
        };
    }, [atlasRef, epoch, regionKey, enabled]);

    useLayoutEffect(() => {
        if (!tip || !body.current) return;
        // offsetHeight remains in atlas pixels even if an HTML preview is scaled.
        const height = body.current.offsetHeight;
        if (height < 1 || height > 104) return;
        let second = null;
        const first = requestAnimationFrame(() => {
            second = requestAnimationFrame(() => {
                if (sequence.current.epoch !== tip.epoch || sequence.current.revision !== tip.revision) return;
                const { epoch: requestEpoch, revision, region, mode: requestMode, button, arrow_x } = tip;
                Promise.resolve(send.current(REQUEST, { epoch: requestEpoch, revision, visible: true, region,
                    mode: requestMode, button, arrow_x, size: [360, height] })).catch(console.error);
            });
        });
        return () => {
            cancelAnimationFrame(first);
            if (second !== null) cancelAnimationFrame(second);
        };
    }, [tip]);

    if (!tip) return null;
    return <>
        <div className={styles.marker} data-tooltip-marker aria-hidden="true">
            {tooltipMarker(tip.epoch, tip.revision).map((bit, i) => <span key={i} style={{ background: bit ? "#fff" : "#000" }} />)}
        </div>
        <div ref={body} role="tooltip" className={styles.body} style={{ "--tip-arrow": `${tip.arrow_x}px` }}>
            <div className={styles.title}><strong>{tip.title}</strong><span>{tip.state}</span></div>
            {tip.help && <p>{tip.help}</p>}
        </div>
    </>;
};
