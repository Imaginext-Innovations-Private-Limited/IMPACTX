import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.pipeline import process_event

HOST = "0.0.0.0"
PORT = 18443
CERT = "certs/localhost-test.crt"
KEY = "certs/localhost-test.key"


class HTTPSHandler(BaseHTTPRequestHandler):
    server_version = "LabHTTPS/1.0"

    def do_GET(self):
        path, _, query = self.path.partition("?")

        event = process_event(
            domain="web",
            event_type="https_request",
            source_ip=self.client_address[0],
            details={
                "service": "https_test",
                "destination_port": PORT,
                "method": "GET",
                "path": path,
                "query_string": query,
                "query_values": [value for _, value in
                                 __import__("urllib.parse", fromlist=["parse_qsl"])
                                 .parse_qsl(query, keep_blank_values=True)],
                "query_keys": [key for key, _ in
                               __import__("urllib.parse", fromlist=["parse_qsl"])
                               .parse_qsl(query, keep_blank_values=True)],
                "user_agent": self.headers.get("User-Agent", "")[:200],
            },
        )

        body = (
            "Universal AI Honeypot Engine\n"
            "Simulated HTTPS service\n"
            f"Event ID: {event['event_id']}\n"
        ).encode()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        pass


def main():
    server = ThreadingHTTPServer((HOST, PORT), HTTPSHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT, KEY)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    print(f"HTTPS test service listening on https://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping HTTPS test service.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
