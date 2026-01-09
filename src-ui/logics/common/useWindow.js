import { useEffect, useRef } from "react";
import { currentMonitor, availableMonitors, PhysicalPosition, PhysicalSize } from "@tauri-apps/api/window";
import { useStdoutToPython } from "@useStdoutToPython";
import { useStore_IsBreakPoint } from "@store";
import { useAppearance } from "@logics_configs";
import { store } from "@store";

export const useWindow = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentUiScaling } = useAppearance();
    const { updateIsBreakPoint } = useStore_IsBreakPoint();

    const appWindow = store.appWindow;

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

        const resizeTimeout = useRef(null);
        const moveTimeout   = useRef(null);
        const unlistenResize = useRef(null);
        const unlistenMove   = useRef(null);

        useEffect(() => {
            const setup = () => {
                unlistenResize.current = appWindow.onResized(() => {
                    clearTimeout(resizeTimeout.current);
                    resizeTimeout.current = setTimeout(() => {
                        asyncSaveWindowGeometry();
                        asyncUpdateBreakPoint();
                    }, 200);
                });

                unlistenMove.current = appWindow.onMoved(() => {
                    clearTimeout(moveTimeout.current);
                    moveTimeout.current = setTimeout(() => {
                        asyncSaveWindowGeometry();
                    }, 200);
                });
            };

            setup();

            return () => {
                if (unlistenResize.current) {
                    unlistenResize.current.then(dispose => dispose());
                }
                if (unlistenMove.current) {
                    unlistenMove.current.then(dispose => dispose());
                }

                clearTimeout(resizeTimeout.current);
                clearTimeout(moveTimeout.current);
            };
        }, []);

        return null;
    };

    const asyncToggleMaximizeApp = async () => {
        const maximizeState = await appWindow.isMaximized();
        if (!maximizeState) {
            await appWindow.maximize();
        } else {
            await appWindow.unmaximize();
        }
    };

    const asyncMinimizeApp = async () => {
        await appWindow.minimize();
    };

    const asyncCloseApp = async () => {
        asyncStdoutToPython("/run/shutdown");
        await new Promise(resolve => setTimeout(resolve, 2000));
        await appWindow.close();
    };

    return {
        WindowGeometryController,
        asyncSaveWindowGeometry,
        restoreWindowGeometry,
        asyncUpdateBreakPoint,

        asyncCloseApp,
        asyncToggleMaximizeApp,
        asyncMinimizeApp,
    };
};
