"""Deterministic CRDT State Projector folding append-only events into materialized views.

All merge rules are commutative, associative, and idempotent over the canonical
total order ``(hlc.wall_ms, hlc.logical, hlc.node_id, event_id)``:

- ``patients``: Per-field Last-Write-Wins Element-Map (LWW-Element-Map), including
  per-key LWW inside ``PatientRecord.metadata``. Concurrent offline edits to
  different fields merge without data loss; edits to the same field converge
  deterministically via HLC total ordering.
- ``triage_history``: Add-wins set of :class:`TriageAssessment` records deduplicated
  by ``assessment_id`` (LWW if updated).
- ``vaccinations``: Per-patient add-wins set keyed by ``(vaccine_code, dose_label)``
  with LWW status updates (e.g. ``DUE_SOON`` -> ``COMPLETED``).
- ``action_cards``: Add-wins set keyed by ``card_id`` with per-field LWW so
  acknowledgement/completion updates from Watch or Phone never get clobbered by
  replayed creation events.
- ``pending_enrichments``: Events with ``enrichment_state == PENDING`` that do not
  yet have a matching ``ENRICHMENT_COMPLETED`` event referencing ``ref_event_id``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aarogya_contracts import (
    ActionCard,
    CrdtEvent,
    EnrichmentState,
    EventType,
    HlcTimestamp,
    PatientRecord,
    TriageAssessment,
    VaccinationDueItem,
)

type _OrderKey = tuple[int, int, str, str]

_PATIENT_SCALAR_FIELDS: frozenset[str] = frozenset(
    {
        "full_name",
        "date_of_birth",
        "age_months",
        "sex",
        "village_id",
        "household_id",
        "is_pregnant",
        "gestational_weeks",
        "preferred_language",
        "registered_by_node",
    }
)

_ACTION_CARD_FIELDS: frozenset[str] = frozenset(
    {
        "patient_id",
        "title",
        "summary",
        "action_steps",
        "priority",
        "severity",
        "status",
        "target_tier",
        "watch_mode",
        "source_event_id",
        "due_by",
        "language",
    }
)


class ProjectedState(BaseModel):
    """Materialized, conflict-free domain state derived solely from the CRDT event log."""

    model_config = ConfigDict(extra="forbid")

    patients: dict[str, PatientRecord] = Field(default_factory=dict)
    triage_history: list[TriageAssessment] = Field(default_factory=list)
    vaccinations: dict[str, list[VaccinationDueItem]] = Field(default_factory=dict)
    action_cards: dict[str, ActionCard] = Field(default_factory=dict)
    checklists: list[CrdtEvent] = Field(default_factory=list)
    outbreak_alerts: list[CrdtEvent] = Field(default_factory=list)
    enrichments: dict[str, CrdtEvent] = Field(default_factory=dict)
    pending_enrichments: list[CrdtEvent] = Field(default_factory=list)
    latest_hlc: HlcTimestamp | None = None
    event_count: int = Field(default=0, ge=0)

    def triage_for_patient(self, patient_id: str) -> list[TriageAssessment]:
        """Return triage history entries for a specific patient."""
        return [item for item in self.triage_history if item.patient_id == patient_id]

    def action_cards_for_patient(self, patient_id: str) -> list[ActionCard]:
        """Return action cards associated with a specific patient."""
        return [card for card in self.action_cards.values() if card.patient_id == patient_id]


def _event_order_key(event: CrdtEvent) -> _OrderKey:
    return (event.hlc.wall_ms, event.hlc.logical, event.hlc.node_id, event.event_id)


def _lww_update(
    registers: dict[str, tuple[_OrderKey, Any]],
    field: str,
    key: _OrderKey,
    value: Any,
) -> None:
    existing = registers.get(field)
    if existing is None or key >= existing[0]:
        registers[field] = (key, value)


def _merge_patient_event(
    patient_fields: dict[str, dict[str, tuple[_OrderKey, Any]]],
    patient_metadata: dict[str, dict[str, tuple[_OrderKey, Any]]],
    event: CrdtEvent,
    order_key: _OrderKey,
) -> None:
    patient_id = event.patient_id or event.payload.get("patient_id")
    if not isinstance(patient_id, str) or not patient_id:
        return

    fields = patient_fields.setdefault(patient_id, {})
    metadata_regs = patient_metadata.setdefault(patient_id, {})

    for field_name in _PATIENT_SCALAR_FIELDS:
        if field_name in event.payload:
            _lww_update(fields, field_name, order_key, event.payload[field_name])

    if "registered_by_node" not in fields:
        fields["registered_by_node"] = (order_key, event.origin_node_id)

    raw_meta = event.payload.get("metadata")
    if isinstance(raw_meta, dict):
        for meta_key, meta_val in raw_meta.items():
            _lww_update(metadata_regs, str(meta_key), order_key, meta_val)


def _materialize_patients(
    patient_fields: dict[str, dict[str, tuple[_OrderKey, Any]]],
    patient_metadata: dict[str, dict[str, tuple[_OrderKey, Any]]],
) -> dict[str, PatientRecord]:
    patients: dict[str, PatientRecord] = {}
    for patient_id in sorted(patient_fields):
        registers = patient_fields[patient_id]
        data: dict[str, Any] = {"patient_id": patient_id}
        for field_name, (_, value) in registers.items():
            data[field_name] = value

        # Safe fallback only when a partial field update arrives before initial registration.
        if not data.get("full_name"):
            data["full_name"] = "Unknown"
        if not data.get("village_id"):
            data["village_id"] = "UNKNOWN"

        # Enforce PatientRecord cross-field invariant when pregnancy ends.
        if data.get("is_pregnant") is False:
            data["gestational_weeks"] = None

        meta_regs = patient_metadata.get(patient_id, {})
        data["metadata"] = {k: meta_regs[k][1] for k in sorted(meta_regs)}
        patients[patient_id] = PatientRecord.model_validate(data)
    return patients


def _merge_action_card_event(
    card_fields: dict[str, dict[str, tuple[_OrderKey, Any]]],
    event: CrdtEvent,
    order_key: _OrderKey,
) -> None:
    payload = event.payload
    raw_card_id = payload.get("card_id")
    if event.event_type == EventType.CHECKLIST_RECORDED and not raw_card_id:
        return
    card_id = str(raw_card_id) if raw_card_id else event.event_id
    registers = card_fields.setdefault(card_id, {})

    if event.patient_id is not None and "patient_id" not in payload:
        _lww_update(registers, "patient_id", order_key, event.patient_id)

    for field_name in _ACTION_CARD_FIELDS:
        if field_name in payload:
            _lww_update(registers, field_name, order_key, payload[field_name])

    if "source_event_id" not in registers:
        registers["source_event_id"] = (order_key, event.ref_event_id or event.event_id)


def _materialize_action_cards(
    card_fields: dict[str, dict[str, tuple[_OrderKey, Any]]],
) -> dict[str, ActionCard]:
    cards: dict[str, ActionCard] = {}
    for card_id in sorted(card_fields):
        registers = card_fields[card_id]
        data: dict[str, Any] = {"card_id": card_id}
        for field_name, (_, value) in registers.items():
            data[field_name] = value
        if not data.get("title"):
            data["title"] = "Action Card"
        if not data.get("summary"):
            data["summary"] = "Pending full card details"
        cards[card_id] = ActionCard.model_validate(data)
    return cards


def project_state(events: Iterable[CrdtEvent]) -> ProjectedState:
    """Fold an arbitrary sequence of CRDT events into a deterministic materialized state.

    Duplicate ``event_id`` entries are ignored and events are sorted by
    ``(hlc.wall_ms, hlc.logical, hlc.node_id, event_id)`` prior to folding, so
    any permutation of the same event set produces an identical ``ProjectedState``.
    """
    unique_events: dict[str, CrdtEvent] = {}
    for event in events:
        if event.event_id not in unique_events:
            unique_events[event.event_id] = event

    ordered_events = sorted(unique_events.values(), key=_event_order_key)
    if not ordered_events:
        return ProjectedState()

    patient_fields: dict[str, dict[str, tuple[_OrderKey, Any]]] = {}
    patient_metadata: dict[str, dict[str, tuple[_OrderKey, Any]]] = {}
    triage_by_id: dict[str, tuple[_OrderKey, TriageAssessment]] = {}
    vaccinations_by_key: dict[str, dict[tuple[str, str], tuple[_OrderKey, VaccinationDueItem]]] = {}
    card_fields: dict[str, dict[str, tuple[_OrderKey, Any]]] = {}
    checklists: list[CrdtEvent] = []
    outbreak_alerts: list[CrdtEvent] = []
    enrichments: dict[str, tuple[_OrderKey, CrdtEvent]] = {}
    pending_candidates: list[CrdtEvent] = []

    for event in ordered_events:
        order_key = _event_order_key(event)

        if event.enrichment_state == EnrichmentState.PENDING:
            pending_candidates.append(event)

        if event.event_type == EventType.PATIENT_REGISTERED:
            _merge_patient_event(patient_fields, patient_metadata, event, order_key)

        elif event.event_type == EventType.TRIAGE_COMPLETED:
            payload = dict(event.payload)
            payload.setdefault("assessment_id", event.event_id)
            if event.patient_id is not None:
                payload.setdefault("patient_id", event.patient_id)
            payload.setdefault("assessed_at_ms", event.hlc.wall_ms)
            assessment = TriageAssessment.model_validate(payload)
            existing = triage_by_id.get(assessment.assessment_id)
            if existing is None or order_key >= existing[0]:
                triage_by_id[assessment.assessment_id] = (order_key, assessment)

        elif event.event_type == EventType.VACCINATION_LOGGED:
            patient_key = event.patient_id or "_unassigned"
            item = VaccinationDueItem.model_validate(event.payload)
            dose_key = (item.vaccine_code, item.dose_label)
            patient_vax = vaccinations_by_key.setdefault(patient_key, {})
            existing_vax = patient_vax.get(dose_key)
            if existing_vax is None or order_key >= existing_vax[0]:
                patient_vax[dose_key] = (order_key, item)

        elif event.event_type == EventType.ACTION_CARD_ISSUED:
            _merge_action_card_event(card_fields, event, order_key)

        elif event.event_type == EventType.CHECKLIST_RECORDED:
            checklists.append(event)
            if "card_id" in event.payload and "status" in event.payload:
                _merge_action_card_event(card_fields, event, order_key)

        elif event.event_type == EventType.OUTBREAK_ALERT_RAISED:
            outbreak_alerts.append(event)

        elif event.event_type == EventType.ENRICHMENT_COMPLETED and event.ref_event_id is not None:
            existing_enr = enrichments.get(event.ref_event_id)
            if existing_enr is None or order_key >= existing_enr[0]:
                enrichments[event.ref_event_id] = (order_key, event)

    patients = _materialize_patients(patient_fields, patient_metadata)
    triage_history = [
        item for _, item in sorted(triage_by_id.values(), key=lambda pair: pair[0])
    ]
    vaccinations: dict[str, list[VaccinationDueItem]] = {}
    for patient_key in sorted(vaccinations_by_key):
        items = [pair[1] for pair in vaccinations_by_key[patient_key].values()]
        items.sort(key=lambda v: (v.due_date, v.vaccine_code, v.dose_label))
        vaccinations[patient_key] = items

    action_cards = _materialize_action_cards(card_fields)
    completed_enrichments = {
        ref_id: enrichments[ref_id][1] for ref_id in sorted(enrichments)
    }
    pending_enrichments = [
        event for event in pending_candidates if event.event_id not in completed_enrichments
    ]

    return ProjectedState(
        patients=patients,
        triage_history=triage_history,
        vaccinations=vaccinations,
        action_cards=action_cards,
        checklists=checklists,
        outbreak_alerts=outbreak_alerts,
        enrichments=completed_enrichments,
        pending_enrichments=pending_enrichments,
        latest_hlc=ordered_events[-1].hlc,
        event_count=len(ordered_events),
    )
