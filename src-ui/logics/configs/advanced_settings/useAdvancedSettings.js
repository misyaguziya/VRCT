import {
    useStore_OscIpAddress,
    useStore_OscPort,
    useStore_EnableWebsocket,
    useStore_WebsocketHost,
    useStore_WebsocketPort,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useNotificationStatus } from "@logics_common";

export const useAdvancedSettings = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { showNotification_Error } = useNotificationStatus();

    // OSC IP Address
    const { currentOscIpAddress, updateOscIpAddress, pendingOscIpAddress } = useStore_OscIpAddress();
    // OSC Port
    const { currentOscPort, updateOscPort, pendingOscPort } = useStore_OscPort();
    // WebSocket
    const { currentEnableWebsocket, updateEnableWebsocket, pendingEnableWebsocket } = useStore_EnableWebsocket();
    const { currentWebsocketHost, updateWebsocketHost, pendingWebsocketHost } = useStore_WebsocketHost();
    const { currentWebsocketPort, updateWebsocketPort, pendingWebsocketPort } = useStore_WebsocketPort();

    // OSC IP Address
    const getOscIpAddress = () => {
        pendingOscIpAddress();
        asyncStdoutToPython("/get/data/osc_ip_address");
    };

    const setOscIpAddress = (osc_ip_address) => {
        pendingOscIpAddress();
        asyncStdoutToPython("/set/data/osc_ip_address", osc_ip_address);
    };

    // OSC Port
    const getOscPort = () => {
        pendingOscPort();
        asyncStdoutToPython("/get/data/osc_port");
    };

    const setOscPort = (osc_port) => {
        pendingOscPort();
        asyncStdoutToPython("/set/data/osc_port", osc_port);
    };

    const saveErrorOscPort = ({data, message, _result}) => {
        updateOscPort(d => d.data);
        showNotification_Error(_result);
    };

    // WebSocket
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
        // OSC IP Address
        currentOscIpAddress,
        getOscIpAddress,
        updateOscIpAddress,
        setOscIpAddress,

        // OSC Port
        currentOscPort,
        getOscPort,
        updateOscPort,
        setOscPort,
        saveErrorOscPort,

        // WebSocket
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