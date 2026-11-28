import socketserver
from services.base_service import BaseService

HOST = "0.0.0.0"
PORT = 13389


class RDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        service = BaseService(
            service_name="rdp_test",
            domain="network",
            port=PORT,
        )

        service.record_event(
            event_type="connection_attempt",
            source_ip=source_ip,
            details={
                "source_port": source_port,
                "protocol": "rdp_test",
                "simulation": True,
            },
        )

        self.request.settimeout(3)

        try:
            data = self.request.recv(4096)

            if data:
                # Record metadata only; don't store raw RDP traffic.
                service.record_event(
                    event_type="rdp_data_received",
                    source_ip=source_ip,
                    details={
                        "bytes_received": len(data),
                        "protocol": "rdp_test",
                        "simulation": True,
                    },
                )
        except (TimeoutError, OSError):
            pass


class RDPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with RDPServer((HOST, PORT), RDPHandler) as server:
        print(f"RDP test simulator listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping RDP test simulator.")


if __name__ == "__main__":
    main()
