import {
    useMessageLogsStatus,
} from "@store";

import { useStdoutToPython } from "./useStdoutToPython";

export const useMessage = () => {
    const { currentMessageLogsStatus, addMessageLogsStatus, updateMessageLogsStatus } = useMessageLogsStatus();
    const { asyncStdoutToPython } = useStdoutToPython();

    return {
        sendMessage: (message) => {
            asyncStdoutToPython({id: "send_message", data: message});
            const uuid = crypto.randomUUID();
            const date = new Date().toLocaleTimeString(
                "ja-JP",
                {hour12: false, hour: "2-digit", minute:"2-digit"},
            );

            addMessageLogsStatus({
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
                updateMessageLogsStatus(updateItemById(uuid));
            }, 3000);
        },
        currentMessageLogsStatus: currentMessageLogsStatus,

        addMessageLogsStatus: (payload) => {
            const data = payload.data;
            const message_object = {
                id: crypto.randomUUID(),
                created_at: new Date().toLocaleTimeString(
                    "ja-JP",
                    {hour12: false, hour: "2-digit", minute:"2-digit"},
                ),
                category: "sent",
                status: "ok",
                messages : {
                    original: data.message,
                    translated: [],
                },
            };
            addMessageLogsStatus(message_object);
        },
    };
};

// const asyncTestFunction = (...args) => {
//     return new Promise((resolve) => {
//         setTimeout(() => {
//             resolve(...args);
//         }, 3000);
//     });
// };