import socketserver

from core.pipeline import process_event

HOST = "0.0.0.0"
PORT = 2121


class FTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        def record(event_type, details):
            return process_event(
                domain="network",
                event_type=event_type,
                source_ip=source_ip,
                details={
                    "service": "ftp_test",
                    "destination_port": PORT,
                    "source_port": source_port,
                    **details,
                },
            )

        record("connection_attempt", {"protocol": "ftp"})
        self.wfile.write(b"220 Universal AI Honeypot FTP ready\r\n")

        for _ in range(10):
            line = self.rfile.readline(2048)
            if not line:
                break

            command_line = line.decode("utf-8", errors="replace").strip()
            command, _, argument = command_line.partition(" ")
            command = command.upper()

            # Never store submitted FTP passwords in event logs.
            safe_argument = (
                "[REDACTED]" if command == "PASS" else argument[:200]
            )

            record(
                "ftp_command",
                {
                    "command": command,
                    "argument": safe_argument,
                },
            )

            if command == "USER":
                self.wfile.write(b"331 Username accepted; password required\r\n")
            elif command == "PASS":
                record(
                    "ftp_login_attempt",
                    {"authentication_failed": True},
                )
                self.wfile.write(b"530 Login incorrect\r\n")
            elif command == "SYST":
                self.wfile.write(b"215 UNIX Type: L8\r\n")
            elif command == "FEAT":
                self.wfile.write(b"211 No additional features\r\n")
            elif command == "QUIT":
                self.wfile.write(b"221 Goodbye\r\n")
                break
            else:
                self.wfile.write(b"502 Command not implemented\r\n")


class FTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with FTPServer((HOST, PORT), FTPHandler) as server:
        print(f"FTP test service listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping FTP test service.")


if __name__ == "__main__":
    main()
