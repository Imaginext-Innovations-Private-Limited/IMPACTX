import sys
import os
import threading
from pathlib import Path
from datetime import datetime, timezone
from math import isfinite

# --------------------------------------------------
# 1. PROJECT PATH CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# --------------------------------------------------
# 2. IMPORTS
# --------------------------------------------------

from flask import Flask, request, jsonify
from flask_cors import CORS

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from detectors.ddos_detector import (
    DDoSDetector,
    FEATURES as DDOS_FEATURES,
)

from detectors.c2_beaconing_detector import (
    C2BeaconingDetector,
    FEATURES as C2_FEATURES,
)

from detectors.data_exfiltration_detector import DataExfiltrationDetector

from detectors.dns_tunnelling_detector import (
    DNSTunnellingDetector,
    FEATURES as DNS_FEATURES,
)

from backend.services.traffic_capture import capture_and_extract
from backend.services.geoip import resolve_session_geo
from backend.services.process_owner import (
    lookup_connection_owners,
    start_owner_sampling,
)
from backend.services.network_info import describe_interfaces
from backend.services.privileges import (
    ELEVATED_FLAG,
    ensure_standard_streams,
    is_elevated,
    is_windows,
    port_in_use,
    relaunch_elevated,
)


# --------------------------------------------------
# 3. FLASK APPLICATION
# --------------------------------------------------

app = Flask(__name__)
CORS(app)


# --------------------------------------------------
# 4. MONGODB CONFIGURATION
# --------------------------------------------------

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

mongo_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=2000,
)

db = mongo_client["cyvora"]
detections = db["detections"]


# --------------------------------------------------
# 5. LOAD FOUR DETECTORS
# --------------------------------------------------

ddos_detector = DDoSDetector()
c2_detector = C2BeaconingDetector()
exfil_detector = DataExfiltrationDetector()
dns_detector = DNSTunnellingDetector()

DETECTORS = {
    "ddos": (ddos_detector, DDOS_FEATURES),
    "c2": (c2_detector, C2_FEATURES),
    "exfiltration": (exfil_detector, exfil_detector.features),
    "dns": (dns_detector, DNS_FEATURES),
}


# --------------------------------------------------
# 6. HOME ROUTE
# --------------------------------------------------

@app.get("/")
def home():
    return jsonify({
        "application": "CYVORA",
        "message": "AI-powered passive network threat detection backend",
        "status": "running",
        "detectors": list(DETECTORS.keys()),
        "capture_api": "/api/capture",
    })


# --------------------------------------------------
# 7. HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health():
    try:
        mongo_client.admin.command("ping")
        mongo_status = "connected"
    except PyMongoError:
        mongo_status = "disconnected"

    return jsonify({
        "status": "running",
        "mongodb": mongo_status,
        "detectors": {name: "loaded" for name in DETECTORS},
        # Live capture needs these rights; without them Windows asks for
        # administrator approval on every capture instead of once.
        "elevated": is_elevated(),
    })


# --------------------------------------------------
# 8. COMMON MANUAL DETECTION FUNCTION
# --------------------------------------------------

def run_detection(name):
    detector, features = DETECTORS[name]
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "success": False,
            "error": "Request must contain a JSON object of feature values",
        }), 400

    missing = [feature for feature in features if feature not in data]
    if missing:
        return jsonify({
            "success": False,
            "error": "Missing required features",
            "missing_features": missing,
        }), 400

    try:
        input_data = {}

        for feature in features:
            value = data[feature]

            if isinstance(value, bool) or value is None:
                raise ValueError(f"{feature} must be numeric")

            number = float(value)
            if not isfinite(number):
                raise ValueError(f"{feature} must be finite")

            input_data[feature] = number

        prediction = detector.predict(input_data)

        if (
            not isinstance(prediction, list)
            or not prediction
            or not isinstance(prediction[0], dict)
        ):
            raise RuntimeError("Unexpected detector output")

        result = prediction[0]

        record = {
            "detector_key": name,
            "detector": result.get("detector", name),
            "prediction": result.get("prediction"),
            "confidence": result.get("confidence"),
            "threshold": result.get("threshold"),
            "features": input_data,
            "source": "manual_api",
            "created_at": datetime.now(timezone.utc),
        }

        try:
            inserted = detections.insert_one(record)
            record_id = str(inserted.inserted_id)
            saved = True
            db_error = None
        except PyMongoError as error:
            record_id = None
            saved = False
            db_error = str(error)

        response = {
            "success": True,
            "result": {
                **result,
                "record_id": record_id,
                "saved_to_database": saved,
            },
        }

        if db_error:
            response["database_warning"] = (
                "Prediction succeeded, but MongoDB storage failed."
            )
            app.logger.error("MongoDB save failed: %s", db_error)

        return jsonify(response), 200

    except (TypeError, ValueError) as error:
        return jsonify({"success": False, "error": str(error)}), 400

    except Exception:
        app.logger.exception("Detection failed: %s", name)
        return jsonify({
            "success": False,
            "error": "Detection failed",
        }), 500


# --------------------------------------------------
# 9. FOUR MANUAL DETECTION APIs
# --------------------------------------------------

@app.post("/api/detect/ddos")
def detect_ddos():
    return run_detection("ddos")


@app.post("/api/detect/c2")
def detect_c2():
    return run_detection("c2")


@app.post("/api/detect/exfiltration")
def detect_exfiltration():
    return run_detection("exfiltration")


@app.post("/api/detect/dns")
def detect_dns():
    return run_detection("dns")


# --------------------------------------------------
# 10. DETECTION HISTORY API
# --------------------------------------------------

@app.get("/api/history")
def get_history():
    try:
        limit = request.args.get("limit", default=50, type=int)

        if limit < 1 or limit > 500:
            return jsonify({
                "success": False,
                "error": "Limit must be between 1 and 500",
            }), 400

        detector_name = request.args.get("detector")
        query = {}

        if detector_name:
            if detector_name not in DETECTORS:
                return jsonify({
                    "success": False,
                    "error": "Unknown detector",
                }), 400
            query["detector_key"] = detector_name

        records = list(
            detections.find(query, {"features": 0})
            .sort("created_at", -1)
            .limit(limit)
        )

        for record in records:
            record["_id"] = str(record["_id"])
            if record.get("created_at"):
                record["created_at"] = record["created_at"].isoformat()

        return jsonify({
            "success": True,
            "count": len(records),
            "history": records,
        })

    except PyMongoError:
        return jsonify({
            "success": False,
            "error": (
                "Unable to retrieve detection history. Check MongoDB."
            ),
        }), 503


# Only one capture can record from an adapter at a time. A second request is
# refused straight away instead of waiting on a busy interface.
_capture_lock = threading.Lock()


# --------------------------------------------------
# 11. LIVE CAPTURE DETECTION HELPERS
# --------------------------------------------------

def _validate_live_features(feature_values, feature_names):
    """Return finite numeric model inputs or raise a clear validation error."""
    if not isinstance(feature_values, dict):
        raise ValueError("Extracted feature record is unavailable")

    missing = [name for name in feature_names if name not in feature_values]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    numeric_values = {}
    for name in feature_names:
        value = feature_values[name]

        # Do not silently invent values for unavailable measurements.
        if value is None or isinstance(value, bool):
            raise ValueError(f"{name} is unavailable or non-numeric")

        number = float(value)
        if not isfinite(number):
            raise ValueError(f"{name} must be finite")

        numeric_values[name] = number

    return numeric_values


def _run_live_detector(
    flow,
    feature_key,
    detector_key,
    detector,
    feature_names,
    result_key,
    model_status,
    summary,
):
    """Run one detector on one flow and persist a successful prediction."""
    feature_values = flow.get(feature_key)

    try:
        input_data = _validate_live_features(feature_values, feature_names)
        predictions = detector.predict(input_data)

        if (
            not isinstance(predictions, list)
            or not predictions
            or not isinstance(predictions[0], dict)
        ):
            raise RuntimeError("Unexpected detector output")

        result = dict(predictions[0])
        result["success"] = True
        result["model_status"] = model_status

        record = {
            "detector_key": detector_key,
            "detector": result.get("detector", detector_key),
            "prediction": result.get("prediction"),
            "confidence": result.get("confidence"),
            "threshold": result.get("threshold"),
            "model_status": model_status,
            "source": "live_capture",
            "features": input_data,
            "created_at": datetime.now(timezone.utc),
        }

        try:
            inserted = detections.insert_one(record)
            result["record_id"] = str(inserted.inserted_id)
            result["saved_to_database"] = True
        except PyMongoError:
            app.logger.exception(
                "Unable to save live %s prediction", detector_key
            )
            result["record_id"] = None
            result["saved_to_database"] = False

        flow[result_key] = result
        summary[detector_key]["predictions_completed"] += 1

    except (TypeError, ValueError) as error:
        # Missing/invalid extracted features are skipped, not fabricated.
        flow[result_key] = {
            "success": False,
            "skipped": True,
            "reason": str(error),
        }
        summary[detector_key]["skipped"] += 1

    except Exception as error:
        app.logger.exception("Live %s prediction failed", detector_key)
        flow[result_key] = {
            "success": False,
            "error": str(error),
        }
        summary[detector_key]["prediction_errors"] += 1


def detect_all_from_captured_flows(capture_result):
    """Run supported live detectors on captured flows.

    Exfiltration and DNS remain available through their manual APIs. Their
    live feature extractors are not yet implemented in flow_features.py.
    """
    flows = capture_result.get("flows", [])

    summary = {
        "ddos": {
            "total_flows": len(flows),
            "predictions_completed": 0,
            "prediction_errors": 0,
            "skipped": 0,
            "model_status": "candidate_experimental",
        },
        "c2": {
            "total_flows": len(flows),
            "predictions_completed": 0,
            "prediction_errors": 0,
            "skipped": 0,
            "model_status": "experimental",
        },
        "exfiltration": {
            "total_flows": len(flows),
            "predictions_completed": 0,
            "prediction_errors": 0,
            "skipped": len(flows),
            "model_status": "manual_api_only",
            "note": "Live CICFlowMeter-compatible feature extraction is not implemented.",
        },
        "dns": {
            "total_flows": len(flows),
            "predictions_completed": 0,
            "prediction_errors": 0,
            "skipped": len(flows),
            "model_status": "manual_api_only",
            "note": "The DNS model's time-window/company aggregation features are not implemented.",
        },
    }

    for flow in flows:
        _run_live_detector(
            flow=flow,
            feature_key="ddos",
            detector_key="ddos",
            detector=ddos_detector,
            feature_names=DDOS_FEATURES,
            result_key="ddos_detection",
            model_status="candidate_experimental",
            summary=summary,
        )

        _run_live_detector(
            flow=flow,
            feature_key="c2",
            detector_key="c2",
            detector=c2_detector,
            feature_names=C2_FEATURES,
            result_key="c2_detection",
            model_status="experimental",
            summary=summary,
        )

        flow["exfiltration_detection"] = {
            "success": False,
            "skipped": True,
            "reason": (
                "Live CICFlowMeter-compatible feature extraction "
                "is not implemented."
            ),
        }

        flow["dns_detection"] = {
            "success": False,
            "skipped": True,
            "reason": (
                "DNS time-window/company aggregation features "
                "are not implemented."
            ),
        }

    capture_result["detection_summary"] = summary
    return capture_result


# --------------------------------------------------
# 12. LIVE NETWORK CAPTURE API
# --------------------------------------------------

@app.post("/api/capture")
def capture_network_traffic():
    data = request.get_json(silent=True)

    if data is None:
        data = {}

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Request body must be a JSON object",
        }), 400

    interface = str(data.get("interface", "4"))
    duration = data.get("duration", 30)

    if not interface.strip():
        return jsonify({
            "success": False,
            "error": "Interface cannot be empty",
        }), 400

    if isinstance(duration, bool) or not isinstance(duration, int):
        return jsonify({
            "success": False,
            "error": "Duration must be an integer",
        }), 400

    if duration < 5 or duration > 60:
        return jsonify({
            "success": False,
            "error": "Duration must be between 5 and 60 seconds",
        }), 400

    if not _capture_lock.acquire(blocking=False):
        return jsonify({
            "success": False,
            "error": (
                "A capture is already running. Wait for it to finish before "
                "starting another one."
            ),
        }), 429

    try:
        # Connections that close during the capture still belong to a process,
        # so the owner table is read before, during and after capturing.
        owners_at_start = lookup_connection_owners()
        sampler = start_owner_sampling()

        try:
            capture_result = capture_and_extract(
                interface=interface,
                duration=duration,
            )
        finally:
            owners_during = sampler.stop()

        capture_result = detect_all_from_captured_flows(capture_result)

        # Map locations come only from addresses observed in this capture.
        capture_result["geo"] = resolve_session_geo(
            capture_result.get("flows", []),
            owners_at_start + owners_during,
        )

        return jsonify({
            "success": True,
            "message": "Network capture and available detector analysis completed",
            "packet_count": capture_result.get("packet_count", 0),
            "flow_count": capture_result.get("flow_count", 0),
            "detection_summary": capture_result.get(
                "detection_summary", {}
            ),
            "geo": capture_result.get("geo", {}),
            "flows": capture_result.get("flows", []),
        }), 200

    except Exception as error:
        app.logger.exception("Network capture failed")

        message = str(error).strip()
        if not message or "TShark" not in message:
            message = "Network capture failed. Check TShark and interface settings."

        return jsonify({"success": False, "error": message}), 500

    finally:
        _capture_lock.release()


# --------------------------------------------------
# 13. CAPTURE INTERFACE NAMES
# --------------------------------------------------

@app.get("/api/network")
def network_interfaces():
    """The capture adapters, with the Wi-Fi network each one is joined to."""
    try:
        return jsonify({"success": True, **describe_interfaces()}), 200
    except Exception:
        app.logger.exception("Interface lookup failed")
        return jsonify({
            "success": False,
            "interfaces": [],
            "ssid": None,
            "interface_id": None,
            "adapter": None,
        }), 200


# --------------------------------------------------
# 14. RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    ensure_standard_streams(PROJECT_ROOT / "backend-server.log")

    # Packet capture is the only part that needs administrator rights. Ask for
    # them once, at start-up, so no capture ever prompts again.
    if is_windows() and not is_elevated() and ELEVATED_FLAG not in sys.argv[1:]:
        if port_in_use():
            print("CYVORA backend is already running on 127.0.0.1:5000.")
            print("Stop it and start the backend again to grant capture rights once.")
            sys.exit(1)

        if relaunch_elevated():
            print("CYVORA needs administrator rights for packet capture.")
            print("Approve the Windows prompt once; the backend restarts itself")
            print("with those rights and never asks again while it runs.")
            sys.exit(0)

        print("Elevation was declined; continuing without it.")
        print("Windows may ask for administrator approval on each capture.")

    print("-----------------------------------")
    print("          CYVORA BACKEND")
    print("-----------------------------------")
    print("Project root:", PROJECT_ROOT)
    print("Detectors loaded:", list(DETECTORS.keys()))
    print("Server: http://127.0.0.1:5000")
    print("Capture API: /api/capture")
    print("Live DDoS detection: enabled (experimental)")
    print("Live C2 detection: enabled when all model features are available")
    print("Live Exfiltration/DNS: manual APIs enabled; live extraction pending")
    print("Capture rights: elevated once at start-up" if is_elevated() else "Capture rights: not elevated")
    print("-----------------------------------")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
    )
