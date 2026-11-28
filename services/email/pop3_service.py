import socketserver

from core.pipeline import process_event

HOST = "0.0.0.0"
PORT = 1110


class POP3Handler(socketserver.StreamRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        def record(event_type, details=None):
            return process_event(
                domain="network",
                event_type=event_type,
                source_ip=source_ip,
                details={
                    "service": "pop3_test",
                    "destination_port": PORT,
                    "source_port": source_port,
                    **(details or {}),
                },
            )

        record("connection_attempt", {"protocol": "pop3"})
        self.wfile.write(b"+OK Universal AI Honeypot POP3 ready\r\n")

        for _ in range(10):
            raw = self.rfile.readline(1024)
            if not raw:
                break

            line = raw.decode("utf-8", errors="replace").strip()
            command, _, argument = line.partition(" ")
            command = command.upper()

            # Never store or log passwords.
            details = {"command": command}
            if command == "USER":
                details["username"] = argument[:100]
            record("pop3_command", details)

            if command == "USER":
                self.wfile.write(b"+OK User accepted\r\n")
            elif command == "PASS":
                record(
                    "pop3_authentication_failed",
                    {"authentication_failed": True},
                )
                self.wfile.write(b"-ERR Authentication failed\r\n")
            elif command == "STAT":
                self.wfile.write(b"+OK 0 0\r\n")
            elif command == "LIST":
                self.wfile.write(b"+OK 0 messages\r\n.\r\n")
            elif command == "NOOP":
                self.wfile.write(b"+OK\r\n")
            elif command == "QUIT":
                self.wfile.write(b"+OK Goodbye\r\n")
                break
            else:
                self.wfile.write(b"-ERR Command not implemented\r\n")


class POP3Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with POP3Server((HOST, PORT), POP3Handler) as server:
        print(f"POP3 test service listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping POP3 test service.")


if __name__ == "__main__":
    main()
