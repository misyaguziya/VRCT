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

            addMessageLogsStatus({
                id: uuid,
                category: "sent",
                status: "pending",
                created_at: generateTimeData(),
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

        addSentMessageLog: (payload) => {
            const data = payload.data;
            const message_object = generateMessageObject(data, "sent");
            addMessageLogsStatus(message_object);
        },
        addReceivedMessageLog: (payload) => {
            const data = payload.data;
            const message_object = generateMessageObject(data, "received");
            addMessageLogsStatus(message_object);
        },
    };
};

const generateTimeData = () => {
    const data = new Date().toLocaleTimeString(
        "ja-JP",
        {hour12: false, hour: "2-digit", minute: "2-digit"},
    );
    return data;
};

const generateMessageObject = (data, category) => {
    return {
        id: crypto.randomUUID(),
        created_at: generateTimeData(),
        category: category,
        status: "ok",
        messages: {
            original: data.message,
            translated: [],
        },
    };
};