import { useStdoutToPython } from "@logics/useStdoutToPython";
import { useEffect } from "react";
import { appWindow, currentMonitor, LogicalPosition, LogicalSize } from "@tauri-apps/api/window";

export const useWindow = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const asyncGetWindowGeometry = async () => {
        try {
            const position = await appWindow.outerPosition();
            const { x, y } = position;

            const size = await appWindow.outerSize();
            const { width, height } = size;

            return {
                x_pos: x,
                y_pos: y,
                width: width,
                height: height
            };
        } catch (err) {
            console.error("Error getting window position and size:", err);
        }
    };

    const asyncSaveWindowGeometry = async () => {
        const data = await asyncGetWindowGeometry();
        asyncStdoutToPython("/set/data/main_window_geometry", data);
    };

    const restoreWindowGeometry = async (data) => {
        try {
            const monitor = await currentMonitor();

            if (monitor) {
                const { width: monitorWidth, height: monitorHeight } = monitor.size;

                let width = Math.min(parseInt(data.width), monitorWidth);
                let height = Math.min(parseInt(data.height), monitorHeight);

                const x = parseInt(data.x_pos);
                const y = parseInt(data.y_pos);

                await appWindow.setPosition(new LogicalPosition(x, y));
                await appWindow.setSize(new LogicalSize(width, height));
            } else {
                console.error("Monitor information could not be retrieved.");
            }
        } catch (err) {
            console.error("Error setting window position and size:", err);
        }
    };

    const fetchAndUpdateWindowGeometry = () => {
        asyncStdoutToPython("/get/data/main_window_geometry");
    };

    const WindowGeometryController = () => {
        useEffect(() => {
            let resizeTimeout;
            const unlistenResize = appWindow.onResized(() => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(asyncSaveWindowGeometry, 200);
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
        fetchAndUpdateWindowGeometry,
        restoreWindowGeometry,
    };
};
