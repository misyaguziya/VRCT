import {
    useStore_EnableWebsocket,
    useStore_WebsocketHost,
    useStore_WebsocketPort,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useWebsocket = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableWebsocket, updateEnableWebsocket, pendingEnableWebsocket } = useStore_EnableWebsocket();
    const { currentWebsocketHost, updateWebsocketHost, pendingWebsocketHost } = useStore_WebsocketHost();
    const { currentWebsocketPort, updateWebsocketPort, pendingWebsocketPort } = useStore_WebsocketPort();

    const getEnableWebsocket = () => {
        pendingEnableWebsocket();
        asyncStdoutToPython("/get/data/websocket_server");
    };

    const toggleEnableWebsocket = () => {
        pendingEnableWebsocket();
        if (currentEnableWebsocket.data) {
            asyncStdoutToPython("/set/disable/websocket_server");
        } else {
            asyncStdoutToPython("/set/enable/websocket_server");
        }
    };


    const getWebsocketHost = () => {
        pendingWebsocketHost();
        asyncStdoutToPython("/get/data/websocket_host");
    };

    const setWebsocketHost = (websocket_host) => {
        pendingWebsocketHost();
        asyncStdoutToPython("/set/data/websocket_host", websocket_host);
    };


    const getWebsocketPort = () => {
        pendingWebsocketPort();
        asyncStdoutToPython("/get/data/websocket_port");
    };

    const setWebsocketPort = (websocket_port) => {
        pendingWebsocketPort();
        asyncStdoutToPython("/set/data/websocket_port", websocket_port);
    };

    return {
        currentEnableWebsocket,
        updateEnableWebsocket,
        getEnableWebsocket,
        toggleEnableWebsocket,

        currentWebsocketHost,
        updateWebsocketHost,
        getWebsocketHost,
        setWebsocketHost,

        currentWebsocketPort,
        updateWebsocketPort,
        getWebsocketPort,
        setWebsocketPort,

    };
};