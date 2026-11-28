from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.pipeline import process_event


class AlternateHTTPHandler(BaseHTTPRequestHandler):
    server_version = "LabHTTP/1.0"

    def do_GET(self):
        event = process_event(
            domain="web",
            event_type="http_request",
            source_ip=self.client_address[0],
            details={
                "service": "alternate_http",
                "destination_port": 18081,
                "method": "GET",
                "path": self.path.split("?", 1)[0],
                "query_string": self.path.split("?", 1)[1]
                if "?" in self.path else "",
                "user_agent": self.headers.get("User-Agent", "")[:200],
            },
        )

        body = (
            "Universal AI Honeypot Engine\n"
            "Simulated HTTP service\n"
            f"Event ID: {event['event_id']}\n"
        ).encode()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        # Requests are already recorded by the event pipeline.
        pass


def main():
    server = ThreadingHTTPServer(("0.0.0.0", 18081), AlternateHTTPHandler)
    print("Alternate HTTP test service listening on 127.0.0.1:18081")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping alternate HTTP test service.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
