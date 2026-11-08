"""Explicit local simulation only. The real PI/DCS workers are not imported."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
import socket
import threading
from urllib.parse import urlsplit

from .core import Coordinator, DemandError, SimulatedSource, Tag, epoch


def demo(sample_seconds=4, context=False):
    return Coordinator(SimulatedSource(), [Tag("DEMO.TEMP", "Suhu demonstrasi", "°C"),
        Tag("DEMO.PRESSURE", "Tekanan demonstrasi", "bar")],
        {"demo-process": ("DEMO.TEMP", "DEMO.PRESSURE"), "demo-temperature": ("DEMO.TEMP",)},
        sample_seconds=sample_seconds, context_tags=("DEMO.TEMP",) if context else ())


def handler(coordinator):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def setup(self):
            self.request.settimeout(3)
            super().setup()

        def log_message(self, *_):
            pass  # Never log leases, owner hashes or payloads.

        def do_GET(self):
            self.send_json({"error": "method_not_allowed"}, 405)

        do_PUT = do_GET
        do_DELETE = do_GET
        do_PATCH = do_GET
        do_OPTIONS = do_GET

        def do_POST(self):
            try:
                host = urlsplit("http://" + self.headers.get("Host", "")).hostname
                if host not in {"127.0.0.1", "localhost", "::1"} or self.headers.get("Origin") is not None:
                    raise DemandError("private_server_only", 403)
                if self.headers.get("Transfer-Encoding") or self.headers.get_content_type() != "application/json":
                    raise DemandError("json_required", 415)
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= 4096:
                    raise DemandError("body_size", 413)
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise DemandError("invalid_request")
                owner = data.get("owner")
                if not isinstance(owner, str) or len(owner) != 64:
                    raise DemandError("invalid_owner")
                route = self.path
                if route == "/v1/historian/subscribe":
                    result = coordinator.subscribe(owner, data.get("client"), data.get("page"))
                elif route == "/v1/historian/heartbeat":
                    result = coordinator.heartbeat(owner, data.get("subscription"))
                elif route == "/v1/historian/release":
                    result = coordinator.release(owner, data.get("subscription"))
                elif route == "/v1/historian/context":
                    result = coordinator.context()
                elif route == "/v1/historian/history":
                    result = coordinator.history(owner, data.get("subscription"), data.get("tag"),
                        epoch(data.get("start")), epoch(data.get("end")), data.get("limit"))
                else:
                    raise DemandError("not_found", 404)
                self.send_json(result)
            except DemandError as error:
                self.send_json({"error": error.code}, error.status)
            except (TypeError, ValueError, KeyError, OverflowError):
                self.send_json({"error": "invalid_request"}, 422)
            except (TimeoutError, ConnectionError, OSError):
                self.close_connection = True
            except Exception:
                self.send_json({"error": "unavailable"}, 503)

        def send_json(self, data, status=200):
            body = json.dumps(data, allow_nan=False).encode()
            if len(body) > 1048576:
                body, status = b'{"error":"response_size"}', 503
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, private")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
    return Handler


class BoundedServer(HTTPServer):
    request_queue_size = 16

    def __init__(self, address, coordinator):
        if not ipaddress.ip_address(address[0]).is_loopback:
            raise ValueError("Loopback only")
        self.slots = threading.BoundedSemaphore(8)
        self.pool = ThreadPoolExecutor(max_workers=8)
        super().__init__(address, handler(coordinator))

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        self.pool.submit(self._finish, request, address)

    def _finish(self, request, address):
        try:
            self.finish_request(request, address)
        except (OSError, TimeoutError):
            pass
        finally:
            self.shutdown_request(request)
            self.slots.release()

    def server_close(self):
        super().server_close()
        self.pool.shutdown(wait=True)


def main():
    parser = argparse.ArgumentParser(description="Volatile, loopback-only historian SIMULATION; no real source access")
    parser.add_argument("--simulation", action="store_true", required=True)
    parser.add_argument("--port", type=int, default=8015)
    parser.add_argument("--sample-seconds", type=int, choices=[3, 4, 5], default=4)
    parser.add_argument("--demo-minute-context", action="store_true", help="Explicit DEMO.TEMP 60s reads while pages are closed")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be 1024..65535")
    # Linux abstract socket is a process owner lock, not a file or data store.
    owner = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        owner.bind("\0nadi-historian-simulation-v1")
    except OSError:
        parser.error("A simulation gateway already owns the shared sampler")
    coordinator = demo(args.sample_seconds, args.demo_minute_context)
    stop = threading.Event()
    def sample():
        while not stop.is_set():
            coordinator.tick()
            stop.wait(0.25)
    worker = threading.Thread(target=sample, daemon=True)
    try:
        with BoundedServer(("127.0.0.1", args.port), coordinator) as server:
            worker.start()
            print("Historian SIMULATION ready on loopback. Values are synthetic; no real source connected.", flush=True)
            try:
                server.serve_forever(poll_interval=0.25)
            except KeyboardInterrupt:
                pass
    finally:
        stop.set()
        if worker.is_alive():
            worker.join(timeout=3)
        owner.close()


if __name__ == "__main__":
    main()
