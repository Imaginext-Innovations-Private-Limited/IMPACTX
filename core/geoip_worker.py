import queue
import threading
import logging

from core.geoip_manager import (
    lookup_ip_geolocation,
    validate_public_ip
)

logger = logging.getLogger(__name__)

_geo_queue = queue.Queue(maxsize=1000)
_queued_ips = set()
_lock = threading.Lock()
_worker_started = False


def _worker():
    while True:
        ip_address = _geo_queue.get()

        try:
            lookup_ip_geolocation(ip_address)
        except Exception:
            logger.exception("Geolocation lookup failed for an IP")
        finally:
            with _lock:
                _queued_ips.discard(ip_address)

            _geo_queue.task_done()


def enqueue_geolocation(ip_address):
    global _worker_started

    try:
        public_ip = validate_public_ip(ip_address)
    except ValueError:
        return False

    if public_ip is None:
        return False

    with _lock:
        if public_ip in _queued_ips:
            return False

        if not _worker_started:
            thread = threading.Thread(
                target=_worker,
                name="geoip-worker",
                daemon=True
            )
            thread.start()
            _worker_started = True

        try:
            _geo_queue.put_nowait(public_ip)
            _queued_ips.add(public_ip)
            return True
        except queue.Full:
            return False
