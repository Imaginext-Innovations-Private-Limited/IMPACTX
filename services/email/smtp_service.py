import socketserver

from core.pipeline import process_event

HOST = "0.0.0.0"
PORT = 2525


class SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        def record(event_type, details=None):
            return process_event(
                domain="network",
                event_type=event_type,
                source_ip=source_ip,
                details={
                    "service": "smtp_test",
                    "destination_port": PORT,
                    "source_port": source_port,
                    **(details or {}),
                },
            )

        record("connection_attempt", {"protocol": "smtp"})
        self.wfile.write(b"220 Universal AI Honeypot SMTP ready\r\n")

        for _ in range(12):
            raw = self.rfile.readline(2048)
            if not raw:
                break

            line = raw.decode("utf-8", errors="replace").strip()
            command, _, argument = line.partition(" ")
            command = command.upper()

            # Do not retain email addresses, message bodies, or credentials.
            safe_details = {"command": command}
            if command in {"EHLO", "HELO"}:
                safe_details["argument"] = "[REDACTED]"
            record("smtp_command", safe_details)

            if command in {"EHLO", "HELO"}:
                self.wfile.write(b"250-localhost\r\n250 HELP\r\n")
            elif command == "MAIL":
                self.wfile.write(b"250 Sender accepted (simulation)\r\n")
            elif command == "RCPT":
                self.wfile.write(b"250 Recipient accepted (simulation)\r\n")
            elif command == "DATA":
                self.wfile.write(
                    b"354 Message content not collected; send a single dot to finish\r\n"
                )
                # Drain the body without logging or storing its contents.
                for _ in range(100):
                    body_line = self.rfile.readline(2048)
                    if not body_line or body_line.strip() == b".":
                        break
                self.wfile.write(b"250 Message discarded by honeypot\r\n")
            elif command == "RSET":
                self.wfile.write(b"250 Reset\r\n")
            elif command == "NOOP":
                self.wfile.write(b"250 OK\r\n")
            elif command == "QUIT":
                self.wfile.write(b"221 Goodbye\r\n")
                break
            else:
                self.wfile.write(b"502 Command not implemented\r\n")


class SMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with SMTPServer((HOST, PORT), SMTPHandler) as server:
        print(f"SMTP test service listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping SMTP test service.")


if __name__ == "__main__":
    main()
