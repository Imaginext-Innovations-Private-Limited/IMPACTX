import socketserver
from services.base_service import BaseService

HOST = "0.0.0.0"
PORT = 1445


class SMBHandler(socketserver.BaseRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        service = BaseService(
            service_name="smb_test",
            domain="network",
            port=PORT,
        )

        service.record_event(
            event_type="connection_attempt",
            source_ip=source_ip,
            details={
                "source_port": source_port,
                "protocol": "smb_test",
                "simulation": True,
            },
        )

        self.request.settimeout(3)

        try:
            data = self.request.recv(4096)

            if data:
                # Log only protocol metadata, never file contents.
                service.record_event(
                    event_type="smb_data_received",
                    source_ip=source_ip,
                    details={
                        "bytes_received": len(data),
                        "protocol": "smb_test",
                        "simulation": True,
                    },
                )

                # SMB uses binary protocol messages, so don't send
                # a fake SMB response that might mislead clients.
        except (TimeoutError, OSError):
            pass


class SMBServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with SMBServer((HOST, PORT), SMBHandler) as server:
        print(f"SMB test simulator listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping SMB test simulator.")


if __name__ == "__main__":
    main()
