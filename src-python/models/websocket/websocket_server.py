"""Manages a WebSocket server for real-time communication, running in a separate thread."""
import asyncio
import threading
from typing import Any, Callable, Coroutine, Optional, Set # Added Coroutine, Any

import websockets # type: ignore
from websockets.exceptions import ConnectionClosed # type: ignore
# Use legacy.server for compatibility if needed, otherwise websockets.server
from websockets.legacy.server import WebSocketServerProtocol # type: ignore
# from websockets.server import WebSocketServerProtocol # Alternative for newer versions

class WebSocketServer:
    """
    Manages a WebSocket server, handling client connections, message broadcasting,
    and graceful shutdown, all within a dedicated asyncio event loop running in a separate thread.
    """
    host: str
    port: int
    clients: Set[WebSocketServerProtocol]
    _message_handler: Optional[Callable[['WebSocketServer', WebSocketServerProtocol, str], None]]
    _loop: Optional[asyncio.AbstractEventLoop]
    _server: Optional[websockets.server.Serve] # Type for the object returned by websockets.serve
    _thread: Optional[threading.Thread]
    _send_queue: Optional[asyncio.Queue[Optional[str]]] # Queue for messages to be sent
    is_running: bool

    def __init__(self, host: str = '127.0.0.1', port: int = 8765) -> None:
        """
        Initializes the WebSocket server with a specified host and port.

        Args:
            host: The host address to bind the server to.
            port: The port number to bind the server to.
        """
        self.host = host
        self.port = port
        self.clients = set()
        self._message_handler = None
        self._loop = None
        self._server = None
        self._thread = None
        self._send_queue = None
        self.is_running = False

    def set_message_handler(self, handler: Callable[['WebSocketServer', WebSocketServerProtocol, str], None]) -> None:
        """
        Sets the callback function to be invoked when a message is received from a client.
        The handler should be a synchronous function: handler(server_instance, websocket_client, message_string).
        """
        self._message_handler = handler

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        """
        Handles an individual client WebSocket session.
        Adds client to active set, listens for messages, invokes message handler,
        and removes client upon disconnection.
        """
        self.clients.add(websocket)
        # print(f"Client connected: {websocket.remote_address}, Total clients: {len(self.clients)}")
        try:
            async for message in websocket:
                if self._message_handler:
                    # Assuming _message_handler is synchronous as per current model.py usage.
                    # If it were async, it would be: await self._message_handler(...)
                    self._message_handler(self, websocket, str(message)) # Ensure message is str
        except ConnectionClosed:
            # print(f"Client disconnected: {websocket.remote_address} (ConnectionClosed)")
            pass
        except Exception as e:
            print(f"Error in client handler {websocket.remote_address}: {e}") # Consider logging
        finally:
            self.clients.remove(websocket)
            # print(f"Client removed: {websocket.remote_address}, Total clients: {len(self.clients)}")

    async def _broadcast_async(self, message: str) -> None:
        """Asynchronously broadcasts a message to all connected clients."""
        if self.clients:
            # Create a list of send tasks to run concurrently
            tasks = [client.send(message) for client in self.clients]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Handle/log exceptions for specific clients if needed
                    # print(f"Error sending to client {list(self.clients)[i].remote_address}: {result}")
                    pass # Optionally remove failing clients

    async def _send_loop(self) -> None:
        """Asynchronous loop that takes messages from an internal queue and broadcasts them."""
        if not self._send_queue: # Should be initialized in setup_server
            print("Send queue not initialized for WebSocket server.") # Consider logging
            return

        while True:
            message = await self._send_queue.get()
            if message is None:  # Shutdown signal
                self._send_queue.task_done() # Acknowledge shutdown signal
                break
            await self._broadcast_async(message)
            self._send_queue.task_done() # Acknowledge message processing

    def send(self, message: str) -> None:
        """
        Thread-safe method to queue a message for broadcasting to all clients.
        This is intended to be called from external synchronous threads (e.g., main app logic).
        """
        if self._loop and self._send_queue and self.is_running:
            try:
                # Use put_nowait as call_soon_threadsafe executes the call in the loop's thread
                self._loop.call_soon_threadsafe(self._send_queue.put_nowait, message)
            except Exception as e: # Catch potential errors if loop/queue is not in expected state
                 print(f"Error queueing message for WebSocket: {e}") # Consider logging
        else:
            print("WebSocket server not running or send queue not available.") # Consider logging


    def broadcast(self, message: str) -> None:
        """
        Deprecated in favor of `send()`. Kept for compatibility if direct async broadcast is needed
        from within the event loop, but `send()` is preferred for external calls.
        To broadcast from another coroutine in the same loop: `await self._broadcast_async(message)`
        To broadcast from a synchronous function (like this one was): use `self.send(message)`
        """
        # This method, if called from a non-async context, needs to schedule _broadcast_async.
        # However, send() is the preferred way for thread-safe external calls.
        # If this is meant to be called from within the event loop by another coroutine:
        #   loop = asyncio.get_running_loop()
        #   loop.create_task(self._broadcast_async(message))
        # If it's for external sync calls, `self.send` is better.
        # For now, making it use `self.send` for simplicity and thread-safety.
        self.send(message)


    def start(self) -> None:
        """Starts the WebSocket server in a new daemon thread."""
        if self._thread and self._thread.is_alive():
            print("WebSocket server thread already running.")
            return
        
        self._thread = threading.Thread(target=self._run_loop, name="WebSocketServerThread", daemon=True)
        self._thread.start()
        print(f"WebSocket server starting on ws://{self.host}:{self.port}...")


    def _run_loop(self) -> None:
        """Runs the asyncio event loop for the WebSocket server in its dedicated thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def setup_server() -> None:
            """Sets up and starts the WebSocket server within the event loop."""
            if not self._loop: return # Should not happen if called from _run_loop
            
            # Initialize the send queue within the loop where it will be used
            self._send_queue = asyncio.Queue() 
            
            # Start the server
            self._server = await websockets.serve(self._handler, self.host, self.port) # type: ignore
            
            # Start the send loop task
            self._loop.create_task(self._send_loop())
            
            self.is_running = True
            print(f"WebSocket server running on ws://{self.host}:{self.port}")

        self._loop.run_until_complete(setup_server())
        
        try:
            self._loop.run_forever()
        except KeyboardInterrupt: # Should be handled by the main thread's KeyboardInterrupt
            pass
        finally:
            print("WebSocket event loop stopping...")
            if self._loop.is_running(): # Ensure loop is running before trying to complete shutdown
                 self._loop.run_until_complete(self._shutdown())
            self._loop.close()
            print("WebSocket event loop closed.")
            self.is_running = False


    async def _shutdown(self) -> None:
        """Gracefully shuts down the WebSocket server and all client connections."""
        print("Shutting down WebSocket server...")
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            print("WebSocket server has been closed.")
        
        # Close all client connections
        # Create a list of close tasks
        if self.clients:
            print(f"Closing {len(self.clients)} client connections...")
            close_tasks = [ws.close(code=1000, reason="Server shutdown") for ws in self.clients]
            await asyncio.gather(*close_tasks, return_exceptions=True) # Handle errors during close
            self.clients.clear()
            print("All client connections closed.")


    def stop(self) -> None:
        """Stops the WebSocket server and its dedicated thread."""
        if not self.is_running or not self._loop:
            print("WebSocket server is not running.")
            return

        print("Stopping WebSocket server...")
        self.is_running = False # Signal loops to stop

        if self._send_queue and self._loop:
            # Signal the _send_loop to terminate
            self._loop.call_soon_threadsafe(self._send_queue.put_nowait, None)

        if self._loop and self._loop.is_running():
            # Signal the main event loop (run_forever) to stop
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0) # Wait for the thread to finish
            if self._thread.is_alive():
                 print("WebSocket server thread did not terminate cleanly.") # Consider logging
        
        self._thread = None
        self._loop = None # Loop is closed in _run_loop's finally block
        print("WebSocket server stopped.")


if __name__ == "__main__":
    # Example usage and test functions
    def message_handler(server: WebSocketServer, websocket: WebSocketServerProtocol, message: str) -> None:
        """Handles messages received from clients."""
        print(f"Received message from {websocket.remote_address}: {message}")
        # Echo the message back to all clients (including the sender)
        server.send(f"Server Echo: {message}")

    def send_periodic_messages(server: WebSocketServer) -> None:
        """Sends a message from the server periodically in a separate thread."""
        print("Starting periodic message sender thread...")
        counter = 0
        while server.is_running: # Check if server is still running
            time.sleep(5)
            if server.is_running: # Double check before sending
                counter += 1
                message_to_send = f"Periodic server message #{counter}"
                print(f"Server sending: {message_to_send}")
                server.send(message_to_send) # Use the thread-safe send method
            else:
                break
        print("Periodic message sender thread stopped.")

    async def main() -> None:
        """Main async function to run the server and test functionality."""
        ws_server: WebSocketServer = WebSocketServer(host='localhost', port=8766)
        ws_server.set_message_handler(message_handler)
        ws_server.start()
        
        # Start a thread to send periodic messages from the server
        send_thread: threading.Thread = threading.Thread(target=send_periodic_messages, args=(ws_server,), daemon=True)
        send_thread.start()

        try:
            # Keep the main coroutine alive, simulating an application main loop
            while ws_server.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("KeyboardInterrupt received in main, stopping server...")
        finally:
            print("Main exiting, ensuring server stop...")
            ws_server.stop() # Ensure server is stopped when main exits
            if send_thread.is_alive():
                send_thread.join(timeout=1) # Wait for sender thread

    if os.name == "nt": # Fix for ProactorLoop in Windows for asyncio with websockets
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application terminated by user.")
    except Exception as e:
        print(f"Application error: {e}")