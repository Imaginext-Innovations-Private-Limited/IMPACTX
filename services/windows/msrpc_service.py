import socketserver
from services.base_service import BaseService

HOST = "0.0.0.0"
PORT = 1135


class MSRPCHandler(socketserver.BaseRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        service = BaseService(
            service_name="msrpc_test",
            domain="network",
            port=PORT,
        )

        service.record_event(
            event_type="connection_attempt",
            source_ip=source_ip,
            details={
                "source_port": source_port,
                "protocol": "msrpc_tcp_test",
                "simulation": True,
            },
        )

        self.request.settimeout(2)

        try:
            data = self.request.recv(1024)

            if data:
                service.record_event(
                    event_type="msrpc_data_received",
                    source_ip=source_ip,
                    details={
                        "bytes_received": len(data),
                        "protocol": "msrpc_tcp_test",
                        "simulation": True,
                    },
                )

                self.request.sendall(
                    b"MSRPC honeypot test endpoint - not a real RPC server\r\n"
                )
        except (TimeoutError, OSError):
            pass


class MSRPCServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with MSRPCServer((HOST, PORT), MSRPCHandler) as server:
        print(f"MS RPC test simulator listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping MS RPC test simulator.")


if __name__ == "__main__":
    main()

