import socket
import struct

from core.pipeline import process_event

HOST = "0.0.0.0"
PORT = 1053


def decode_name(packet, offset):
    labels = []

    while offset < len(packet):
        length = packet[offset]
        offset += 1

        if length == 0:
            break

        # Ignore compressed names for this minimal test implementation.
        if length & 0xC0:
            raise ValueError("Compressed DNS names are not supported")

        if offset + length > len(packet):
            raise ValueError("Invalid DNS label length")

        labels.append(packet[offset:offset + length].decode("ascii", errors="replace"))
        offset += length

    return ".".join(labels), offset


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"DNS UDP test service listening on {HOST}:{PORT}")

    try:
        while True:
            packet, peer = sock.recvfrom(4096)

            try:
                if len(packet) < 17:
                    continue

                transaction_id, flags, qdcount = struct.unpack("!HHH", packet[:6])

                if qdcount != 1:
                    continue

                domain, offset = decode_name(packet, 12)

                if offset + 4 > len(packet):
                    continue

                qtype, qclass = struct.unpack("!HH", packet[offset:offset + 4])

                process_event(
                    domain="network",
                    event_type="dns_query",
                    source_ip=peer[0],
                    details={
                        "service": "dns_test",
                        "destination_port": PORT,
                        "transport": "udp",
                        "query_name": domain[:253],
                        "query_type": qtype,
                        "query_class": qclass,
                    },
                )

                # Return a safe, simulated NXDOMAIN response.
                response_flags = 0x8183
                header = struct.pack(
                    "!HHHHHH",
                    transaction_id,
                    response_flags,
                    1,
                    0,
                    0,
                    0,
                )

                question = packet[12:offset + 4]
                sock.sendto(header + question, peer)

            except (ValueError, struct.error):
                continue
    except KeyboardInterrupt:
        print("\nStopping DNS test service.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
