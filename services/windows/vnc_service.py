import socketserver
from services.base_service import BaseService

HOST = "0.0.0.0"
PORT = 15900


class VNCHandler(socketserver.BaseRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        service = BaseService(
            service_name="vnc_test",
            domain="network",
            port=PORT,
        )

        service.record_event(
            event_type="connection_attempt",
            source_ip=source_ip,
            details={
                "source_port": source_port,
                "protocol": "vnc_test",
                "simulation": True,
            },
        )

        self.request.settimeout(3)

        try:
            data = self.request.recv(4096)

            if data:
                # Record metadata only; never store raw traffic.
                service.record_event(
                    event_type="vnc_data_received",
                    source_ip=source_ip,
                    details={
                        "bytes_received": len(data),
                        "protocol": "vnc_test",
                        "simulation": True,
                    },
                )
        except (TimeoutError, OSError):
            pass


class VNCServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with VNCServer((HOST, PORT), VNCHandler) as server:
        print(f"VNC test simulator listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping VNC test simulator.")


if __name__ == "__main__":
    main()
