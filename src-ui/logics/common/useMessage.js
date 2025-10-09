import {
    useStore_MessageLogs,
    useStore_MessageInputValue,
} from "@store";

import { useStdoutToPython } from "@useStdoutToPython";

export const useMessage = () => {
    const { currentMessageLogs, addMessageLogs, updateMessageLogs } = useStore_MessageLogs();
    const { currentMessageInputValue, updateMessageInputValue } = useStore_MessageInputValue();
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
                original: { message: message, transliteration: [] },
                translations: [],
            },
        });
    };

    const addSystemMessageLog = (message) => {
        const uuid = crypto.randomUUID();
        const date = generateTimeData();

        addMessageLogs({
            id: uuid,
            category: "system",
            status: "system",
            created_at: date,
            messages: {
                original: { message: message, transliteration: [] },
                translations: [],
            },
        });
    };

    const addSystemMessageLog_FromBackend = (payload) => {
        addSystemMessageLog(payload.message);
    };

    const updateSentMessageLogById = (payload) => {
        updateMessageLogs(updateItemById(payload.id, payload));
    };

    const addSentMessageLog = (payload) => {
        const message_object = generateMessageObject(payload, "sent");
        addMessageLogs(message_object);
    };

    const addReceivedMessageLog = (payload) => {
        const message_object = generateMessageObject(payload, "received");
        addMessageLogs(message_object);
    };

    const startTyping = () => {
        asyncStdoutToPython("/run/typing_message_box");
    };

    const stopTyping = () => {
        asyncStdoutToPython("/run/stop_typing_message_box");
    };

    return {
        currentMessageLogs,
        sendMessage,
        addSystemMessageLog,
        addSystemMessageLog_FromBackend,
        updateSentMessageLogById,
        addSentMessageLog,
        addReceivedMessageLog,

        currentMessageInputValue,
        updateMessageInputValue,

        startTyping,
        stopTyping,
    };
};

const generateTimeData = () => {
    return new Date().toLocaleTimeString(
        "ja-JP",
        { hour12: false, hour: "2-digit", minute: "2-digit" }
    );
};

const generateMessageObject = (data, category) => {
    return {
        id: crypto.randomUUID(),
        created_at: generateTimeData(),
        category: category,
        status: "ok",
        messages: {
            original: data.original,
            translations: data.translations ?? [],
        },
    };
};

const updateItemById = (id, updated_data) => (current_items) => {
    return current_items.data.map(item => {
        if (item.id === id) {
            item.status = "ok";
            if (updated_data.translations) item.messages.translations = updated_data.translations;
        }
        return item;
    });
};