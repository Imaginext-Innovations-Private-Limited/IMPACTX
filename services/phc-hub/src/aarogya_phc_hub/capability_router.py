"""Capability-proportional task router for Aarogya Mesh."""

from __future__ import annotations

from enum import StrEnum

from aarogya_contracts import (
    ExecutionTarget,
    HardwareCapabilityManifest,
    NodeTier,
)


class WorkloadKind(StrEnum):
    """Supported edge workloads evaluated by the Capability Router."""

    DETERMINISTIC_TRIAGE = "DETERMINISTIC_TRIAGE"
    VACCINE_SCHEDULE = "VACCINE_SCHEDULE"
    TINY_RISK_CHECK = "TINY_RISK_CHECK"
    VOICE_ASR = "VOICE_ASR"
    CLINICAL_SLM_STRUCTURING = "CLINICAL_SLM_STRUCTURING"
    OUTBREAK_DETECTION = "OUTBREAK_DETECTION"


_MIN_TINY_ML_BATTERY_PCT = 20
_MIN_PHONE_TINY_ML_RAM_MB = 2048
_MIN_HUB_RAM_MB = 4096


def route_workload(
    manifest: HardwareCapabilityManifest,
    workload: WorkloadKind,
    *,
    required_model: str | None = None,
) -> ExecutionTarget:
    """Deterministically route a workload from a node's HardwareCapabilityManifest.

    Clinical safety invariant: deterministic WHO IMNCI / ASHA triage and UIP
    vaccine scheduling ALWAYS execute locally (`LOCAL_DETERMINISTIC`) on all tiers.
    """
    if workload in (WorkloadKind.DETERMINISTIC_TRIAGE, WorkloadKind.VACCINE_SCHEDULE):
        return ExecutionTarget.LOCAL_DETERMINISTIC

    model_present = (
        True
        if required_model is None
        else any(required_model in model for model in manifest.installed_models)
    )

    if workload == WorkloadKind.TINY_RISK_CHECK:
        if manifest.tier == NodeTier.TIER_2_HUB:
            return ExecutionTarget.LOCAL_TINY_ML
        if (
            manifest.battery_pct >= _MIN_TINY_ML_BATTERY_PCT
            and model_present
            and (manifest.tier == NodeTier.TIER_1_PHONE and manifest.ram_mb >= _MIN_PHONE_TINY_ML_RAM_MB)
        ):
            return ExecutionTarget.LOCAL_TINY_ML
        if (
            manifest.tier == NodeTier.TIER_0_WATCH
            and manifest.battery_pct >= _MIN_TINY_ML_BATTERY_PCT
            and required_model is not None
            and model_present
        ):
            return ExecutionTarget.LOCAL_TINY_ML
        return ExecutionTarget.DEFER_TO_HUB

    if workload in (WorkloadKind.VOICE_ASR, WorkloadKind.CLINICAL_SLM_STRUCTURING):
        if manifest.tier == NodeTier.TIER_2_HUB and manifest.ram_mb >= _MIN_HUB_RAM_MB:
            return ExecutionTarget.LOCAL_TINY_ML
        return ExecutionTarget.DEFER_TO_HUB

    if workload == WorkloadKind.OUTBREAK_DETECTION:
        if manifest.tier == NodeTier.TIER_2_HUB:
            return ExecutionTarget.LOCAL_DETERMINISTIC
        return ExecutionTarget.DEFER_TO_HUB

    return ExecutionTarget.DEFER_TO_HUB
