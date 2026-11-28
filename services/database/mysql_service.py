import socket
import socketserver
import struct

from core.pipeline import process_event

HOST = "0.0.0.0"
PORT = 13306


def mysql_packet(payload, sequence=0):
    length = len(payload)
    return (
        length.to_bytes(3, "little")
        + bytes([sequence])
        + payload
    )


def recv_exact(sock, size):
    data = bytearray()

    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data.extend(chunk)

    return bytes(data)


class MySQLHandler(socketserver.BaseRequestHandler):
    def handle(self):
        source_ip, source_port = self.client_address

        def record(event_type, details=None):
            return process_event(
                domain="network",
                event_type=event_type,
                source_ip=source_ip,
                details={
                    "service": "mysql_test",
                    "destination_port": PORT,
                    "source_port": source_port,
                    **(details or {}),
                },
            )

        record("connection_attempt", {"protocol": "mysql"})

        # MySQL protocol-v10 greeting.
        server_version = b"8.0.0-honeypot\x00"
        connection_id = struct.pack("<I", 1)

        auth_data = b"0123456789abcdefghij"

        capabilities = (
            0x00000001 |  # CLIENT_LONG_PASSWORD
            0x00000004 |  # CLIENT_LONG_FLAG
            0x00000200 |  # CLIENT_PROTOCOL_41
            0x00008000 |  # CLIENT_SECURE_CONNECTION
            0x00080000    # CLIENT_PLUGIN_AUTH
        )

        greeting = (
            b"\x0a"
            + server_version
            + connection_id
            + auth_data[:8]
            + b"\x00"
            + struct.pack("<H", capabilities & 0xFFFF)
            + b"\x21"
            + struct.pack("<H", 0x0002)
            + struct.pack("<H", (capabilities >> 16) & 0xFFFF)
            + b"\x15"
            + b"\x00" * 10
            + auth_data[8:]
            + b"\x00"
            + b"mysql_native_password\x00"
        )

        self.request.settimeout(5)

        try:
            self.request.sendall(mysql_packet(greeting, 0))

            # Read the client handshake without retaining its contents.
            header = recv_exact(self.request, 4)

            if header is None:
                record("mysql_client_disconnected", {})
                return

            payload_length = int.from_bytes(header[:3], "little")

            if payload_length < 32 or payload_length > 65536:
                record("mysql_protocol_rejected", {})
                return

            client_handshake = recv_exact(
                self.request, payload_length
            )

            if client_handshake is None:
                record("mysql_client_disconnected", {})
                return

            # Never log or retain client authentication data.
            record(
                "mysql_authentication_attempt",
                {"authentication_failed": True},
            )

            message = b"Access denied (honeypot simulation)"

            error_payload = (
                b"\xff"
                + struct.pack("<H", 1045)
                + b"#28000"
                + message
            )

            self.request.sendall(mysql_packet(error_payload, 2))

        except (socket.timeout, ConnectionError, OSError):
            record("mysql_client_disconnected", {})


class MySQLServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with MySQLServer((HOST, PORT), MySQLHandler) as server:
        print(f"MySQL test service listening on {HOST}:{PORT}")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping MySQL test service.")


if __name__ == "__main__":
    main()
