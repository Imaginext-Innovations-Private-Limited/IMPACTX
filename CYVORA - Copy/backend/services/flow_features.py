
from collections import defaultdict
import numpy as np
import pandas as pd


def build_bidirectional_flows(packets):
    """Group packets into bidirectional network flows."""

    grouped = defaultdict(list)

    for packet in packets:
        src = (packet["src_ip"], packet["src_port"])
        dst = (packet["dst_ip"], packet["dst_port"])

        endpoints = sorted([src, dst])
        key = (
            endpoints[0],
            endpoints[1],
            packet["protocol"]
        )

        grouped[key].append(packet)

    return list(grouped.values())


def _directional_stats(packets, forward_src):
    forward = []
    backward = []

    for packet in packets:
        endpoint = (packet["src_ip"], packet["src_port"])

        if endpoint == forward_src:
            forward.append(packet)
        else:
            backward.append(packet)

    return forward, backward


def _iat_stats(packets):
    times = sorted(p["timestamp"] for p in packets)

    if len(times) < 2:
        return [0.0] * 5

    intervals = np.diff(times) * 1_000_000

    return [
        float(np.sum(intervals)),
        float(np.mean(intervals)),
        float(np.std(intervals)),
        float(np.max(intervals)),
        float(np.min(intervals)),
    ]


def extract_ddos_features(packets):
    """Extract the exact 19 DDoS model input columns."""

    if not packets:
        raise ValueError("No packets in flow")

    packets = sorted(packets, key=lambda p: p["timestamp"])

    first = packets[0]
    forward_src = (first["src_ip"], first["src_port"])

    fwd, bwd = _directional_stats(packets, forward_src)

    flow_iat = _iat_stats(packets)
    fwd_iat = _iat_stats(fwd)
    bwd_iat = _iat_stats(bwd)

    return {
        "flw_duration": (
            packets[-1]["timestamp"] - packets[0]["timestamp"]
        ) * 1_000_000,
        "fwd_pkt_total": len(fwd),
        "bwd_pkt_total": len(bwd),
        "fwd_pkt_len_total": sum(p["length"] for p in fwd),
        "bwd_pkt_len_total": sum(p["length"] for p in bwd),
        "flw_iat_mean": flow_iat[1],
        "flw_iat_std": flow_iat[2],
        "flw_iat_max": flow_iat[3],
        "flw_iat_min": flow_iat[4],
        "fwd_iat_total": fwd_iat[0],
        "fwd_iat_mean": fwd_iat[1],
        "fwd_iat_std": fwd_iat[2],
        "fwd_iat_max": fwd_iat[3],
        "fwd_iat_min": fwd_iat[4],
        "bwd_iat_total": bwd_iat[0],
        "bwd_iat_mean": bwd_iat[1],
        "bwd_iat_std": bwd_iat[2],
        "bwd_iat_max": bwd_iat[3],
        "bwd_iat_min": bwd_iat[4],
    }


def extract_c2_features(packets):
    """Extract the C2 model's eight expected columns."""

    if not packets:
        raise ValueError("No packets in flow")

    packets = sorted(packets, key=lambda p: p["timestamp"])

    first = packets[0]
    forward_src = (first["src_ip"], first["src_port"])

    fwd, bwd = _directional_stats(packets, forward_src)

    return {
        "duration": (
            packets[-1]["timestamp"] - packets[0]["timestamp"]
        ),
        "orig_bytes": sum(p["length"] for p in fwd),
        "resp_bytes": sum(p["length"] for p in bwd),
        "orig_pkts": len(fwd),
        "resp_pkts": len(bwd),
        "orig_ip_bytes": sum(p["length"] for p in fwd),
        "resp_ip_bytes": sum(p["length"] for p in bwd),
        "missed_bytes": None,
    }


def extract_all_flows(packets):
    """Create feature records for captured bidirectional flows."""

    results = []

    for flow in build_bidirectional_flows(packets):
        results.append({
            "packets": flow,
            "ddos": extract_ddos_features(flow),
            "c2": extract_c2_features(flow),
        })

    return results
