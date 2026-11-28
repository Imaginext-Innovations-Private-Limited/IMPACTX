import socket
import threading

from services.base_service import BaseService


class TCPHoneypotListener:
    """Minimal local TCP listener for adapter integration tests."""

    def __init__(self, service_name, port, banner=b"Lab service ready\r\n"):
        self.service = BaseService(
            service_name=service_name,
            domain="network",
            port=port,
        )
        self.port = port
        self.banner = banner

    def handle_client(self, client, address):
        source_ip, source_port = address

        try:
            self.service.record_event(
                event_type="connection_attempt",
                source_ip=source_ip,
                details={"source_port": source_port},
            )
            client.sendall(self.banner)
        except (OSError, ValueError) as error:
            print(f"Client handling error: {error}")
        finally:
            client.close()

    def serve_once(self):
        """Accept one local connection, record it, then exit."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", self.port))
            server.listen(1)
            print(f"{self.service.service_name} test listener on 127.0.0.1:{self.port}")

            client, address = server.accept()
            self.handle_client(client, address)


if __name__ == "__main__":
    listener = TCPHoneypotListener(
        service_name="tcp_adapter_test",
        port=18080,
    )
    listener.serve_once()
