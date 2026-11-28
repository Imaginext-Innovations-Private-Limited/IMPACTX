import socketserver

from core.pipeline import process_event

HOST = "0.0.0.0"
PORT = 1143


class IMAPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        def record(event_type, details=None):
            return process_event(
                domain="network",
                event_type=event_type,
                source_ip=source_ip,
                details={
                    "service": "imap_test",
                    "destination_port": PORT,
                    "source_port": source_port,
                    **(details or {}),
                },
            )

        record("connection_attempt", {"protocol": "imap"})
        self.wfile.write(b"* OK Universal AI Honeypot IMAP ready\r\n")

        for _ in range(12):
            raw = self.rfile.readline(2048)
            if not raw:
                break

            line = raw.decode("utf-8", errors="replace").strip()
            parts = line.split(None, 2)

            if len(parts) < 2:
                continue

            tag, command = parts[0], parts[1].upper()
            argument = parts[2] if len(parts) > 2 else ""

            details = {"command": command}

            if command == "LOGIN":
                # Never log usernames or passwords from LOGIN.
                details["credentials"] = "[REDACTED]"

            record("imap_command", details)

            if command == "CAPABILITY":
                self.wfile.write(
                    b"* CAPABILITY IMAP4rev1 IMAP4rev2\r\n"
                    + f"{tag} OK CAPABILITY completed\r\n".encode()
                )
            elif command == "NOOP":
                self.wfile.write(f"{tag} OK NOOP completed\r\n".encode())
            elif command == "LOGIN":
                record(
                    "imap_authentication_failed",
                    {"authentication_failed": True},
                )
                self.wfile.write(
                    f"{tag} NO Authentication failed\r\n".encode()
                )
            elif command == "LOGOUT":
                self.wfile.write(
                    b"* BYE Logging out\r\n"
                    + f"{tag} OK LOGOUT completed\r\n".encode()
                )
                break
            else:
                self.wfile.write(
                    f"{tag} BAD Command not implemented\r\n".encode()
                )


class IMAPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with IMAPServer((HOST, PORT), IMAPHandler) as server:
        print(f"IMAP test service listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping IMAP test service.")


if __name__ == "__main__":
    main()
