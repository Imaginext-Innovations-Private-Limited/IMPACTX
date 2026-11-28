import socketserver
import struct

from core.pipeline import process_event

HOST = "0.0.0.0"
PORT = 15432


class PostgreSQLHandler(socketserver.StreamRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        def record(event_type, details=None):
            return process_event(
                domain="network",
                event_type=event_type,
                source_ip=source_ip,
                details={
                    "service": "postgres_test",
                    "destination_port": PORT,
                    "source_port": source_port,
                    **(details or {}),
                },
            )

        record("connection_attempt", {"protocol": "postgresql"})

        try:
            # Read PostgreSQL's length-prefixed startup packet.
            header = self.rfile.read(4)
            if len(header) != 4:
                return

            length = struct.unpack("!I", header)[0]
            if length < 8 or length > 65536:
                return

            body = self.rfile.read(length - 4)
            if len(body) != length - 4:
                return

            protocol = struct.unpack("!I", body[:4])[0]

            # SSLRequest: decline TLS on this local test service.
            if protocol == 80877103:
                self.wfile.write(b"N")
                header = self.rfile.read(4)
                if len(header) != 4:
                    return

                length = struct.unpack("!I", header)[0]
                if length < 8 or length > 65536:
                    return

                body = self.rfile.read(length - 4)
                if len(body) != length - 4:
                    return

                protocol = struct.unpack("!I", body[:4])[0]

            if protocol != 196608:  # PostgreSQL protocol 3.0
                record("postgres_protocol_rejected", {})
                return

            record("postgres_startup", {"protocol_version": "3.0"})

            # AuthenticationCleartextPassword request.
            auth_request = b"R" + struct.pack("!II", 8, 3)
            self.wfile.write(auth_request)

            # Read one client message; never log its contents.
            message_type = self.rfile.read(1)
            length_bytes = self.rfile.read(4)
            if len(message_type) != 1 or len(length_bytes) != 4:
                return

            message_length = struct.unpack("!I", length_bytes)[0]
            if message_length < 4 or message_length > 65536:
                return

            message_body = self.rfile.read(message_length - 4)
            if len(message_body) != message_length - 4:
                return

            if message_type == b"p":
                record(
                    "postgres_authentication_attempt",
                    {"authentication_failed": True},
                )

                error_fields = (
                    b"SERROR\x00"
                    b"VERROR\x00"
                    b"C28P01\x00"
                    b"MAuthentication failed (honeypot simulation)\x00"
                    b"\x00"
                )
                error_packet = (
                    b"E" + struct.pack("!I", len(error_fields) + 4)
                    + error_fields
                )
                self.wfile.write(error_packet)
            else:
                record("postgres_unexpected_client_message", {})

        except (ConnectionError, OSError, struct.error):
            record("postgres_client_disconnected", {})


class PostgreSQLServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with PostgreSQLServer((HOST, PORT), PostgreSQLHandler) as server:
        print(f"PostgreSQL test service listening on {HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping PostgreSQL test service.")


if __name__ == "__main__":
    main()
