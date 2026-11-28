"""Strict Pydantic v2 domain contracts for Aarogya Mesh.

Every tier (Tier-0 Watch, Tier-1 CHW Phone, Tier-2 PHC Hub) and every module
(clinical-engine, crdt-sync, phc-hub, ml-pipeline, field-pwa, watch-companion)
communicates exclusively through these versioned, schema-verified models.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT_SCHEMA_VERSION = "1.0.0"


class NodeTier(StrEnum):
    """Hardware capability tier of an autonomous Aarogya Mesh node."""

    TIER_0_WATCH = "TIER_0_WATCH"
    TIER_1_PHONE = "TIER_1_PHONE"
    TIER_2_HUB = "TIER_2_HUB"


class WatchMode(StrEnum):
    """Dual operating mode for a Tier-0 Watch companion."""

    CHW_COMPANION = "CHW_COMPANION"
    PATIENT_FAMILY = "PATIENT_FAMILY"


class ExecutionTarget(StrEnum):
    """Capability-proportional routing decision for a workload."""

    LOCAL_DETERMINISTIC = "LOCAL_DETERMINISTIC"
    LOCAL_TINY_ML = "LOCAL_TINY_ML"
    DEFER_TO_HUB = "DEFER_TO_HUB"


class HardwareCapabilityManifest(BaseModel):
    """Self-advertised hardware profile of a mesh node."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., min_length=1, max_length=128)
    tier: NodeTier
    ram_mb: int = Field(..., ge=1)
    cpu_cores: int = Field(..., ge=1)
    battery_pct: int = Field(default=100, ge=0, le=100)
    has_npu: bool = False
    installed_models: list[str] = Field(default_factory=list)
    watch_mode: WatchMode | None = None

    @model_validator(mode="after")
    def _validate_watch_mode(self) -> HardwareCapabilityManifest:
        if self.tier == NodeTier.TIER_0_WATCH:
            if self.watch_mode is None:
                self.watch_mode = WatchMode.CHW_COMPANION
        elif self.watch_mode is not None:
            raise ValueError("watch_mode is only valid when tier is TIER_0_WATCH")
        return self


class HlcTimestamp(BaseModel):
    """Hybrid Logical Clock timestamp with deterministic total ordering."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    wall_ms: int = Field(..., ge=0)
    logical: int = Field(default=0, ge=0)
    node_id: str = Field(..., min_length=1, max_length=128)

    def as_tuple(self) -> tuple[int, int, str]:
        """Return canonical total-order comparison key."""
        return (self.wall_ms, self.logical, self.node_id)

    def to_sort_key(self) -> str:
        """Return lexicographically sortable representation for SQLite cursors."""
        return f"{self.wall_ms:016d}:{self.logical:06d}:{self.node_id}"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, HlcTimestamp):
            return NotImplemented
        return self.as_tuple() < other.as_tuple()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, HlcTimestamp):
            return NotImplemented
        return self.as_tuple() <= other.as_tuple()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, HlcTimestamp):
            return NotImplemented
        return self.as_tuple() > other.as_tuple()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, HlcTimestamp):
            return NotImplemented
        return self.as_tuple() >= other.as_tuple()


class EventType(StrEnum):
    """Append-only event taxonomy for the CRDT event log."""

    PATIENT_REGISTERED = "PATIENT_REGISTERED"
    TRIAGE_COMPLETED = "TRIAGE_COMPLETED"
    CHECKLIST_RECORDED = "CHECKLIST_RECORDED"
    VACCINATION_LOGGED = "VACCINATION_LOGGED"
    VOICE_NOTE_RECORDED = "VOICE_NOTE_RECORDED"
    ENRICHMENT_COMPLETED = "ENRICHMENT_COMPLETED"
    ACTION_CARD_ISSUED = "ACTION_CARD_ISSUED"
    OUTBREAK_ALERT_RAISED = "OUTBREAK_ALERT_RAISED"


class EnrichmentState(StrEnum):
    """Deferred Hub ML enrichment lifecycle state on a CRDT event."""

    NOT_NEEDED = "NOT_NEEDED"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CrdtEvent(BaseModel):
    """Immutable append-only event exchanged across autonomous mesh nodes."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    hlc: HlcTimestamp
    origin_node_id: str = Field(..., min_length=1, max_length=128)
    patient_id: str | None = Field(default=None, min_length=1, max_length=128)
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    enrichment_state: EnrichmentState = EnrichmentState.NOT_NEEDED
    ref_event_id: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def _validate_enrichment_reference(self) -> CrdtEvent:
        if self.event_type == EventType.ENRICHMENT_COMPLETED and self.ref_event_id is None:
            raise ValueError("ENRICHMENT_COMPLETED events must specify ref_event_id")
        return self


class PatientRecord(BaseModel):
    """Materialized community patient profile."""

    model_config = ConfigDict(extra="forbid")

    patient_id: str = Field(..., min_length=1, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)
    date_of_birth: date | None = None
    age_months: int | None = Field(default=None, ge=0, le=1500)
    sex: Literal["F", "M", "O", "U"] = "U"
    village_id: str = Field(..., min_length=1, max_length=128)
    household_id: str | None = Field(default=None, min_length=1, max_length=128)
    is_pregnant: bool = False
    gestational_weeks: int | None = Field(default=None, ge=0, le=45)
    preferred_language: str = Field(default="en", min_length=2, max_length=16)
    registered_by_node: str | None = Field(default=None, min_length=1, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_pregnancy_fields(self) -> PatientRecord:
        if self.gestational_weeks is not None and not self.is_pregnant:
            raise ValueError("gestational_weeks requires is_pregnant=True")
        return self


class TriageSeverity(StrEnum):
    """Deterministic WHO IMNCI / NHM ASHA triage classification."""

    GREEN_HOME = "GREEN_HOME"
    YELLOW_PHC = "YELLOW_PHC"
    RED_EMERGENCY = "RED_EMERGENCY"


class TriageAssessment(BaseModel):
    """Deterministic clinical triage outcome with mandatory red-flag safety invariant."""

    model_config = ConfigDict(extra="forbid")

    assessment_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    patient_id: str | None = Field(default=None, min_length=1, max_length=128)
    severity: TriageSeverity
    matched_rules: list[str] = Field(default_factory=list)
    immediate_actions: list[str] = Field(default_factory=list)
    referral_required: bool = False
    rationale: str = Field(..., min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    protocol_source: str = Field(default="WHO_IMNCI_ASHA_DETERMINISTIC", min_length=1, max_length=128)
    execution_target: ExecutionTarget = ExecutionTarget.LOCAL_DETERMINISTIC
    assessed_at_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _validate_clinical_safety_floor(self) -> TriageAssessment:
        if self.severity == TriageSeverity.RED_EMERGENCY and not self.referral_required:
            raise ValueError("RED_EMERGENCY triage assessment must set referral_required=True")
        return self


class VaccinationStatus(StrEnum):
    """Immunization schedule adherence status."""

    OVERDUE = "OVERDUE"
    DUE_SOON = "DUE_SOON"
    UPCOMING = "UPCOMING"
    COMPLETED = "COMPLETED"


class VaccinationDueItem(BaseModel):
    """Single dose schedule item under the India Universal Immunization Programme (UIP)."""

    model_config = ConfigDict(extra="forbid")

    vaccine_code: str = Field(..., min_length=1, max_length=64)
    vaccine_name: str = Field(..., min_length=1, max_length=160)
    dose_label: str = Field(..., min_length=1, max_length=64)
    due_date: date
    status: VaccinationStatus
    administered_date: date | None = None
    days_delta: int = 0
    reminder_text: str = Field(default="", max_length=500)
    schedule_group: str = Field(default="UIP_INDIA", min_length=1, max_length=64)

    @model_validator(mode="after")
    def _validate_completed_date(self) -> VaccinationDueItem:
        if self.status == VaccinationStatus.COMPLETED and self.administered_date is None:
            raise ValueError("COMPLETED vaccination item must include administered_date")
        return self


class ActionCardPriority(StrEnum):
    """Urgency tier for CHW or Patient-Family action cards."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionCardStatus(StrEnum):
    """Lifecycle state of an action card across synced nodes."""

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"


class ActionCard(BaseModel):
    """Compact, glanceable action item synced across Hub, Phone, and Watch."""

    model_config = ConfigDict(extra="forbid")

    card_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    patient_id: str | None = Field(default=None, min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=160)
    summary: str = Field(..., min_length=1, max_length=1000)
    action_steps: list[str] = Field(default_factory=list)
    priority: ActionCardPriority = ActionCardPriority.MEDIUM
    severity: TriageSeverity | None = None
    status: ActionCardStatus = ActionCardStatus.OPEN
    target_tier: NodeTier = NodeTier.TIER_0_WATCH
    watch_mode: WatchMode | None = None
    source_event_id: str | None = Field(default=None, min_length=1, max_length=128)
    due_by: date | None = None
    language: str = Field(default="en", min_length=2, max_length=16)


class SyncEnvelope(BaseModel):
    """Peer-to-peer delta sync payload exchanged over local LAN/Hotspot/WebSocket."""

    model_config = ConfigDict(extra="forbid")

    envelope_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    sender_manifest: HardwareCapabilityManifest
    sender_hlc: HlcTimestamp
    since_cursor: str | None = Field(default=None, max_length=256)
    next_cursor: str | None = Field(default=None, max_length=256)
    events: list[CrdtEvent] = Field(default_factory=list)
    ack_event_ids: list[str] = Field(default_factory=list)
    schema_version: str = Field(default=CONTRACT_SCHEMA_VERSION, min_length=1, max_length=32)


CORE_CONTRACT_MODELS: dict[str, type[BaseModel]] = {
    "HardwareCapabilityManifest": HardwareCapabilityManifest,
    "HlcTimestamp": HlcTimestamp,
    "CrdtEvent": CrdtEvent,
    "PatientRecord": PatientRecord,
    "TriageAssessment": TriageAssessment,
    "VaccinationDueItem": VaccinationDueItem,
    "ActionCard": ActionCard,
    "SyncEnvelope": SyncEnvelope,
}
