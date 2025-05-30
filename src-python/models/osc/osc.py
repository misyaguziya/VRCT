"""Handles OSC (Open Sound Control) communication, including sending messages and discovering/querying OSC parameters via OSCQuery."""
import asyncio
from threading import Thread
from time import sleep
from typing import Any, Callable, Dict, Optional # Added Optional, Callable, Dict

# Third-party imports
from pythonosc import dispatcher, osc_server, udp_client
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.shared.node import OSCAccess
from tinyoscquery.utility import get_open_tcp_port, get_open_udp_port

try:
    from utils import errorLogging # Local application import
except ImportError:
    import traceback # Standard library
    def errorLogging() -> None: # Added type hint
        """Basic error logging if the main utils.errorLogging is not available."""
        print("Error occurred:", traceback.format_exc())

class OSCHandler:
    """Manages OSC client/server operations and OSCQuery interactions."""
    is_osc_query_enabled: bool
    osc_ip_address: str
    osc_port: int
    osc_parameter_muteself: str
    osc_parameter_chatbox_typing: str
    osc_parameter_chatbox_input: str
    udp_client: udp_client.SimpleUDPClient
    osc_server_name: str
    osc_server: Optional[osc_server.ThreadingOSCUDPServer]
    osc_query_service: Optional[OSCQueryService]
    osc_query_service_name: str
    osc_server_ip_address: str # Should this be the same as osc_ip_address or local IP?
    http_port: Optional[int]
    osc_server_port: Optional[int]
    dict_filter_and_target: Dict[str, Callable[..., Any]]
    browser: Optional[OSCQueryBrowser]

    def __init__(self, ip_address: str = "127.0.0.1", port: int = 9000) -> None:
        """Initializes OSC client, server details, parameter paths, and OSCQuery status."""
        if ip_address in ["127.0.0.1", "localhost"]:
            self.is_osc_query_enabled = True
        else:
            self.is_osc_query_enabled = False

        self.osc_ip_address = ip_address
        self.osc_port = port
        self.osc_parameter_muteself = "/avatar/parameters/MuteSelf"
        self.osc_parameter_chatbox_typing = "/chatbox/typing"
        self.osc_parameter_chatbox_input = "/chatbox/input"
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)
        
        self.osc_server_name = "VRChat-Client" # Name of the service to look for via OSCQuery
        self.osc_server: Optional[osc_server.ThreadingOSCUDPServer] = None
        
        self.osc_query_service_name = "VRCT" # Name of this application's OSCQuery service
        self.osc_query_service: Optional[OSCQueryService] = None
        
        # Assuming osc_server_ip_address should be the local IP for the server to bind to.
        # The provided ip_address is for the client (VRChat).
        # For a server, it's typically "0.0.0.0" or a specific local IP.
        # For OSCQuery to work locally and be discoverable, binding to localhost is common.
        self.osc_server_ip_address = "127.0.0.1" # Defaulting to localhost for the server
        
        self.http_port: Optional[int] = None # For OSCQuery HTTP server
        self.osc_server_port: Optional[int] = None # For this app's OSC server
        
        self.dict_filter_and_target: Dict[str, Callable[..., Any]] = {}
        self.browser: Optional[OSCQueryBrowser] = None

    def getIsOscQueryEnabled(self) -> bool:
        """Checks if OSCQuery is active (based on localhost IP for the target client)."""
        return self.is_osc_query_enabled

    def setOscIpAddress(self, ip_address: str) -> None:
        """Updates OSC target IP, reinitializes client and server if running."""
        if ip_address in ["127.0.0.1", "localhost"]:
            self.is_osc_query_enabled = True
        else:
            self.is_osc_query_enabled = False

        self.oscServerStop() # Stop server before changing IP
        self.osc_ip_address = ip_address
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)
        self.receiveOscParameters() # Re-initialize server with new settings if applicable

    def setOscPort(self, port: int) -> None:
        """Updates OSC target port, reinitializes client and server if running."""
        self.oscServerStop() # Stop server before changing port
        self.osc_port = port
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)
        self.receiveOscParameters() # Re-initialize server

    def sendTyping(self, flag: bool = False) -> None:
        """Sends OSC message for typing status (/chatbox/typing)."""
        try:
            self.udp_client.send_message(self.osc_parameter_chatbox_typing, [flag])
        except Exception as e:
            errorLogging(f"Error sending OSC typing message: {e}")

    def sendMessage(self, message: str = "", notification: bool = True) -> None:
        """Sends OSC chat message (/chatbox/input) with optional notification sound."""
        if len(message) > 0:
            try:
                self.udp_client.send_message(self.osc_parameter_chatbox_input, [f"{message}", True, notification])
            except Exception as e:
                errorLogging(f"Error sending OSC message: {e}")

    def getOSCParameterValue(self, address: str) -> Any:
        """
        Retrieves an OSC parameter's value using OSCQuery.
        Handles browser initialization and errors. Returns None on failure or if OSCQuery is disabled.
        """
        if not self.is_osc_query_enabled:
            return None

        value: Any = None
        try:
            if self.browser is None:
                self.browser = OSCQueryBrowser()
                # Initial sleep might be long, consider if it's always needed or can be shorter/conditional
                sleep(1) 

            # Find the VRChat client's OSCQuery service
            # This assumes VRChat client is running and discoverable.
            service = self.browser.find_service_by_name(self.osc_server_name) # e.g., "VRChat-Client"
            if service is not None:
                osc_query_client = OSCQueryClient(service)
                parameter_node = osc_query_client.query_node(address) # Query for the specific parameter
                if parameter_node and parameter_node.value: # Check if node and value exist
                    value = parameter_node.value[0] # Assuming single value in the list
            else:
                # This is a common case if VRChat isn't running or OSCQuery is off in VRChat.
                # errorLogging(f"OSCQuery service '{self.osc_server_name}' not found.") # Potentially too verbose
                pass
        except Exception as e:
            errorLogging(f"Error getting OSC parameter value for {address}: {e}")
            # Reset browser on error to attempt re-initialization next time
            if self.browser is not None:
                try:
                    self.browser.zc.close() # Close ZeroConf browser
                    # self.browser.browser.cancel() # Assuming this is for a specific browser implementation if present
                except Exception as e_close:
                    errorLogging(f"Error closing OSCQueryBrowser components: {e_close}")
                finally:
                    self.browser = None # Ensure reset
        return value

    def getOSCParameterMuteSelf(self) -> Optional[bool]:
        """Helper to get the 'MuteSelf' OSC parameter value. Returns None if not found or error."""
        value = self.getOSCParameterValue(self.osc_parameter_muteself)
        if isinstance(value, bool):
            return value
        # Could also log if value is not None but also not bool, indicating unexpected type
        # errorLogging(f"MuteSelf parameter returned non-boolean value: {value}") if value is not None else None
        return None


    def setDictFilterAndTarget(self, dict_filter_and_target: Dict[str, Callable[..., Any]]) -> None:
        """Sets dispatcher rules for the OSC server (address filter to callback function)."""
        self.dict_filter_and_target = dict_filter_and_target

    def receiveOscParameters(self) -> None:
        """
        Starts the OSC server and OSCQuery service (if enabled), advertising endpoints.
        This method attempts to find open ports and initialize the services.
        """
        if not self.is_osc_query_enabled:
            print("OSCQuery is disabled; OSC server will not start.")
            return

        try:
            self.osc_server_port = get_open_udp_port()
            self.http_port = get_open_tcp_port() # For OSCQuery's HTTP server
        except Exception as e:
            errorLogging(f"Failed to get open ports for OSC server/query: {e}")
            return # Cannot proceed without ports

        osc_dispatcher = dispatcher.Dispatcher()
        for address_filter, target_callback in self.dict_filter_and_target.items():
            osc_dispatcher.map(address_filter, target_callback)
        
        try:
            self.osc_server = osc_server.ThreadingOSCUDPServer(
                (self.osc_server_ip_address, self.osc_server_port), osc_dispatcher
            )
            # Start server in a separate thread
            server_thread = Thread(target=self.oscServerServe, daemon=True)
            server_thread.start()
            print(f"OSC Server listening on {self.osc_server_ip_address}:{self.osc_server_port}")
        except Exception as e:
            errorLogging(f"Failed to start OSC server: {e}")
            self.osc_server = None # Ensure server is None if it failed to start
            return # Cannot proceed if OSC server fails

        # Attempt to start OSCQueryService, retry if it fails initially (e.g. port still in use)
        for attempt in range(3): # Retry up to 3 times
            try:
                self.osc_query_service = OSCQueryService(
                    service_name=self.osc_query_service_name,
                    http_port=self.http_port,
                    osc_port=self.osc_server_port, # Advertise the port our OSC server is on
                    # host=self.osc_server_ip_address # May need to specify host if not localhost
                )
                for address_filter in self.dict_filter_and_target.keys():
                    # Advertise endpoints with appropriate access (defaulting to READWRITE)
                    self.osc_query_service.advertise_endpoint(address_filter, access=OSCAccess.READWRITE_VALUE)
                print(f"OSCQuery Service '{self.osc_query_service_name}' started on HTTP port {self.http_port}, advertising OSC port {self.osc_server_port}.")
                break # Success
            except Exception as e:
                errorLogging(f"Failed to start OSCQueryService (attempt {attempt + 1}): {e}")
                self.osc_query_service = None # Ensure it's None on failure
                if attempt < 2: # If not the last attempt
                    sleep(1) # Wait a bit before retrying
                else:
                    print("OSCQueryService failed to start after multiple attempts. Continuing without OSCQuery.")
                    # Optionally, stop the OSC server if OSCQuery is critical
                    # self.oscServerStop() 
                    break 


    def oscServerServe(self) -> None:
        """Internal method to run the OSC server's event loop. This blocks until shutdown."""
        if self.osc_server:
            try:
                # The poll_interval parameter in serve_forever is for the select timeout,
                # not how often it "polls" in a CPU-intensive way.
                # Default python-osc server is already efficient.
                # Reducing it from 10s to 1s for better responsiveness if needed for other reasons,
                # but original 10s is fine for just listening.
                self.osc_server.serve_forever(poll_interval=1.0) 
            except Exception as e:
                errorLogging(f"Exception in OSC server loop: {e}")
            finally:
                print("OSC Server has shut down.")


    def oscServerStop(self) -> None:
        """Stops the OSC server, OSCQuery service, and cleans up OSCQuery browser resources."""
        if isinstance(self.osc_server, osc_server.ThreadingOSCUDPServer):
            try:
                self.osc_server.shutdown() # Request server shutdown
                self.osc_server.server_close() # Close the server socket
                print("OSC Server shut down requested.")
            except Exception as e:
                errorLogging(f"Error shutting down OSC server: {e}")
            finally:
                self.osc_server = None

        if isinstance(self.osc_query_service, OSCQueryService):
            try:
                # OSCQueryService from tinyoscquery might have a specific stop/shutdown method
                # For http.server, shutdown is on the server instance itself.
                # Assuming osc_query_service.http_server is the actual HTTPServer instance.
                if hasattr(self.osc_query_service, 'http_server') and self.osc_query_service.http_server:
                    self.osc_query_service.http_server.shutdown() # Shutdown http server
                    self.osc_query_service.http_server.server_close() # Close socket
                # If OSCQueryService has its own stop method for ZeroConf etc.
                if hasattr(self.osc_query_service, 'stop'):
                    self.osc_query_service.stop()
                print("OSCQuery Service shut down requested.")
            except Exception as e:
                errorLogging(f"Error shutting down OSCQuery service: {e}")
            finally:
                self.osc_query_service = None
        
        if self.browser is not None:
            try:
                self.browser.stop_ exploración() # Assuming this is the correct method for tinyoscquery's browser
                if hasattr(self.browser, 'zc') and self.browser.zc: # If using zeroconf directly
                    self.browser.zc.close()
                print("OSCQuery Browser stopped.")
            except Exception as e:
                errorLogging(f"Error stopping OSCQuery browser: {e}")
            finally:
                self.browser = None

if __name__ == "__main__":
    # Example usage for OSCHandler.
    handler: OSCHandler = OSCHandler()
    
    # Define callback type for clarity
    OscCallbackType = Callable[[str, Any], None]

    def print_handler(address: str, *args: Any) -> None:
        print(f"Received {address} with args {args}")

    handler.setDictFilterAndTarget({
        "/avatar/parameters/MuteSelf": print_handler,
        "/chatbox/typing": print_handler,
        "/chatbox/input": print_handler,
    })
    handler.receiveOscParameters()
    
    print("OSC Server and Query Service started (if enabled). Testing send functions...")
    sleep(5)
    handler.sendTyping(True)
    sleep(1)
    handler.sendMessage(message="Hello World 1", notification=True)
    sleep(10)

    print("IP address changed to 192.168.193.2")
    handler.setOscIpAddress("192.168.193.2")
    sleep(5)
    handler.sendMessage(message="Hello World 2", notification=True)

    print("IP address changed to 127.0.0.1")
    handler.setOscIpAddress("127.0.0.1")
    sleep(5)
    handler.sendMessage(message="Hello World 3", notification=True)
    sleep(10)
    handler.oscServerStop()