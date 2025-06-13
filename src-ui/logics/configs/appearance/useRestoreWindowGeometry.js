// import { useStore_RestoreWindowGeometry } from "@store";
// import { useStdoutToPython } from "@useStdoutToPython";

// export const useRestoreWindowGeometry = () => {
//     const { asyncStdoutToPython } = useStdoutToPython();
//     const { currentRestoreWindowGeometry, updateRestoreWindowGeometry, pendingRestoreWindowGeometry } = useStore_RestoreWindowGeometry();

//     const getRestoreWindowGeometry = () => {
//         pendingRestoreWindowGeometry();
//         asyncStdoutToPython("/get/data/restore_main_window_geometry");
//     };

//     const toggleRestoreWindowGeometry = () => {
//         pendingRestoreWindowGeometry();
//         if (currentRestoreWindowGeometry.data) {
//             asyncStdoutToPython("/set/disable/restore_main_window_geometry");
//         } else {
//             asyncStdoutToPython("/set/enable/restore_main_window_geometry");
//         }
//     };

//     return {
//         currentRestoreWindowGeometry,
//         getRestoreWindowGeometry,
//         toggleRestoreWindowGeometry,
//         updateRestoreWindowGeometry,
//     };
// };