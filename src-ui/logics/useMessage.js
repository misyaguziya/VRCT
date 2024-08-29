import {
    useMessageLogsStatus,
} from "@store";

import { useStdoutToPython } from "./useStdoutToPython";

export const useMessage = () => {
    const { currentMessageLogsStatus, addMessageLogsStatus, updateMessageLogsStatus } = useMessageLogsStatus();
    const { asyncStdoutToPython } = useStdoutToPython();

    return {
        sendMessage: (message) => {
            const uuid = crypto.randomUUID();
            const send_message_object = {
                id: uuid,
                message: message,
            };
            asyncStdoutToPython("/controller/callback_messagebox_press_key_enter", send_message_object);

            addMessageLogsStatus({
                id: uuid,
                category: "sent",
                status: "pending",
                created_at: generateTimeData(),
                messages: {
                    original: message,
                    translated: [],
                },
            });
        },
        currentMessageLogsStatus: currentMessageLogsStatus,

        updateSentMessageLog: (payload) => {
            const data = payload.data;
            updateMessageLogsStatus(updateItemById(data.id));
        },
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


const updateItemById = (id) => (prev_items) => {
    return prev_items.map(item => {
        if (item.id === id) {
            item.status = "ok";
        }
        return item;
    });
};