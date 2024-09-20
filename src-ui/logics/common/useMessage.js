import {
    useStore_MessageLogs,
} from "@store";

import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMessage = () => {
    const { currentMessageLogs, addMessageLogs, updateMessageLogs } = useStore_MessageLogs();
    const { asyncStdoutToPython } = useStdoutToPython();

    const sendMessage = (message) => {
        const uuid = crypto.randomUUID();
        const send_message_object = {
            id: uuid,
            message: message,
        };
        asyncStdoutToPython("/run/send_message_box", send_message_object);

        addMessageLogs({
            id: uuid,
            category: "sent",
            status: "pending",
            created_at: generateTimeData(),
            messages: {
                original: message,
                translated: [],
            },
        });
    };

    const updateSentMessageLogById = (payload) => {
        updateMessageLogs(updateItemById(payload.id, payload.translation));
    };
    const addSentMessageLog = (payload) => {
        const message_object = generateMessageObject(payload, "sent");
        addMessageLogs(message_object);
    };
    const addReceivedMessageLog = (payload) => {
        const message_object = generateMessageObject(payload, "received");
        addMessageLogs(message_object);
    };

    return {
        currentMessageLogs,
        sendMessage,
        updateSentMessageLogById,
        addSentMessageLog,
        addReceivedMessageLog,
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
            translated: data.translation,
        },
    };
};


const updateItemById = (id, translated_data) => (prev_items) => {
    return prev_items.map(item => {
        if (item.id === id) {
            item.status = "ok";
            item.messages.translated = translated_data;
        }
        return item;
    });
};