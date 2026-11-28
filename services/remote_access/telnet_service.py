import socketserver

from core.pipeline import process_event

HOST = "0.0.0.0"
PORT = 2323


class TelnetHandler(socketserver.StreamRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        def record(event_type, details=None):
            return process_event(
                domain="network",
                event_type=event_type,
                source_ip=source_ip,
                details={
                    "service": "telnet_test",
                    "destination_port": PORT,
                    "source_port": source_port,
                    **(details or {}),
                },
            )

        record("connection_attempt", {"protocol": "telnet"})
        self.wfile.write(b"Universal AI Honeypot - simulated Telnet\r\n")
        self.wfile.write(b"login: ")

        username = self.rfile.readline(256).decode(
            "utf-8", errors="replace"
        ).strip()

        if not username:
            return

        record("telnet_login_attempt", {"username": username[:100]})
        self.wfile.write(b"Password: ")

        # Read but never store or log the submitted password.
        password = self.rfile.readline(256)
        del password

        record(
            "telnet_authentication_failed",
            {"authentication_failed": True},
        )
        self.wfile.write(b"\r\nLogin incorrect\r\n")
        self.wfile.write(b"Connection closed\r\n")


class TelnetServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with TelnetServer((HOST, PORT), TelnetHandler) as server:
        print(f"Telnet test service listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping Telnet test service.")


if __name__ == "__main__":
    main()
