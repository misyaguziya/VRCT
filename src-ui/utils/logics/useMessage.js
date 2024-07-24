import {
    useMessageLogs,
} from "@store";

import { useStdoutToPython } from "./useStdoutToPython";

export const useMessage = () => {
    const { currentMessageLogs, addMessageLogs, updateMessageLogs } = useMessageLogs();
    const { asyncStdoutToPython } = useStdoutToPython();

    return {
        sendMessage: (message) => {
            asyncStdoutToPython({id: "send_message", data: message});
            const uuid = crypto.randomUUID();
            const date = new Date().toLocaleTimeString(
                "ja-JP",
                {hour12: false, hour: "2-digit", minute:"2-digit"},
            );

            addMessageLogs({
                id: uuid,
                category: "sent",
                status: "pending",
                created_at: date,
                messages: {
                    original: message,
                    translated: [
                        message,
                    ],
                },
            });

            setTimeout(() => {
                const updateItemById = (id) => (prevItems) => {
                    return prevItems.map(item => {
                        if (item.id === id) {
                            item.status = "ok";
                        }
                        return item;
                    });
                };
                updateMessageLogs(updateItemById(uuid));
            }, 3000);
        },
        currentMessageLogs: currentMessageLogs,
    };
};

// const asyncTestFunction = (...args) => {
//     return new Promise((resolve) => {
//         setTimeout(() => {
//             resolve(...args);
//         }, 3000);
//     });
// };