import { useEffect } from "react";
import { appWindow, currentMonitor, availableMonitors, PhysicalPosition, PhysicalSize } from "@tauri-apps/api/window";
import { useStdoutToPython } from "@logics/useStdoutToPython";
import { useStore_IsBreakPoint } from "@store";
import { useUiScaling } from "@logics_configs";

export const useWindow = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentUiScaling } = useUiScaling();
    const { updateIsBreakPoint } = useStore_IsBreakPoint();

    const asyncGetWindowGeometry = async () => {
        try {
            const position = await appWindow.outerPosition();
            const { x: x_pos, y: y_pos } = position;

            const size = await appWindow.outerSize();
            const { width, height } = size;

            return {
                x_pos: x_pos,
                y_pos: y_pos,
                width: width,
                height: height
            };
        } catch (err) {
            console.error("Error getting window position and size:", err);
        }
    };

    const asyncSaveWindowGeometry = async () => {
        const minimized = await appWindow.isMinimized();
        if (minimized === true) return; // don't save while the window is minimized.
        const data = await asyncGetWindowGeometry();
        asyncStdoutToPython("/set/data/main_window_geometry", data);
    };

    const restoreWindowGeometry = async (data) => {
        try {
            const monitors = await availableMonitors();
            const { x_pos, y_pos, width, height } = data;

            // ウィンドウが属するモニターを特定
            const targetMonitor = monitors.find(monitor =>
                x_pos >= monitor.position.x &&
                y_pos >= monitor.position.y &&
                x_pos < monitor.position.x + monitor.size.width &&
                y_pos < monitor.position.y + monitor.size.height
            ) || await currentMonitor();

            if (targetMonitor) {
                const { width: monitorWidth, height: monitorHeight } = targetMonitor.size;
                const { x: monitorX, y: monitorY } = targetMonitor.position;

                // ウィンドウのサイズをモニターサイズ内に収める
                let adjustedWidth = Math.min(parseInt(width), monitorWidth);
                let adjustedHeight = Math.min(parseInt(height), monitorHeight);

                // ウィンドウの位置をモニターの範囲内に収める
                let adjustedX = parseInt(x_pos);
                let adjustedY = parseInt(y_pos);

                // X座標がモニター左にはみ出ている場合
                if (adjustedX < monitorX) {
                    adjustedX = monitorX;
                }
                // X座標がモニター右にはみ出ている場合
                else if (adjustedX + adjustedWidth > monitorX + monitorWidth) {
                    adjustedX = monitorX + monitorWidth - adjustedWidth;
                }

                // Y座標がモニター上にはみ出ている場合
                if (adjustedY < monitorY) {
                    adjustedY = monitorY;
                }
                // Y座標がモニター下にはみ出ている場合
                else if (adjustedY + adjustedHeight > monitorY + monitorHeight) {
                    adjustedY = monitorY + monitorHeight - adjustedHeight;
                }

                await appWindow.setPosition(new PhysicalPosition(adjustedX, adjustedY));
                await appWindow.setSize(new PhysicalSize(adjustedWidth, adjustedHeight));
            } else {
                console.error("Monitor information could not be retrieved.");
            }
        } catch (err) {
            console.error("Error setting window position and size:", err);
        }
    };

    const asyncUpdateBreakPoint = async () => {
        const size = await appWindow.innerSize();
        const dynamicBreakPoint = 800 * (currentUiScaling.data / 100);
        updateIsBreakPoint(size.width <= dynamicBreakPoint);
    };

    const WindowGeometryController = () => {
        useEffect(() => {
            let resizeTimeout;
            const asyncFunction = () => {
                asyncSaveWindowGeometry();
                asyncUpdateBreakPoint();
            };

            const unlistenResize = appWindow.onResized(() => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(asyncFunction, 200);
            });

            return () => {
                unlistenResize.then((dispose) => dispose());
            };
        }, []);

        useEffect(() => {
            let moveTimeout;
            const unlistenMove = appWindow.onMoved(() => {
                clearTimeout(moveTimeout);
                moveTimeout = setTimeout(asyncSaveWindowGeometry, 200);
            });

            return () => {
                unlistenMove.then((dispose) => dispose());
            };
        }, []);

        return null;
    };

    return {
        WindowGeometryController,
        asyncSaveWindowGeometry,
        restoreWindowGeometry,
        asyncUpdateBreakPoint,
    };
};
