"""Data models shared by every stage of the pipeline."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Origin(str, Enum):
    BILL = "bill"                    # read from the bill by OCR or PDF text
    USER = "user_confirmed"          # typed or corrected by the user
    RULE_DATA = "rule_data"          # taken from an official reference table
    COMPUTED = "computed"            # derived by code from other figures


class Role(str, Enum):
    BILLED_AMOUNT = "billed_amount"
    UNIT_RATE = "unit_rate"
    QUANTITY = "quantity"
    MRP = "mrp"
    GST_RATE = "gst_rate"
    GST_AMOUNT = "gst_amount"
    CEILING_EX_GST = "ceiling_ex_gst"
    CEILING_WITH_GST = "ceiling_with_gst"
    ALLOWED_AMOUNT = "allowed_amount"
    EXPECTED_AMOUNT = "expected_amount"
    EXCESS = "excess"
    TOTAL = "total"
    DAYS = "days"
    NIGHTS = "nights"
    BENCHMARK = "benchmark"
    COUNT = "count"
    SCHEME_COVER = "scheme_cover"          # most a government scheme pays (from schemes.yaml)
    COVERED = "covered"                    # part of a bill a scheme package would include
    POTENTIAL_SAVING = "potential_saving"  # what a scheme could have paid: awareness, never claimable
    INCOME_LIMIT = "income_limit"
    SHARE = "share"
    WAIT_DAYS = "wait_days"                # how long an office has to reply (escalation.yaml)
    TIME_LIMIT = "time_limit"              # how long the family has to file (escalation.yaml)
    DEDUCTED = "deducted"                  # an amount an insurer cut from a claim (typed by the family)


class Verdict(str, Enum):
    RED = "red"
    AMBER = "amber"
    GREY = "grey"
    GREEN = "green"
    INFO = "info"


class Channel(str, Enum):
    HOSPITAL_DESK = "hospital_desk"
    SCHEME = "scheme_grievance"
    NPPA = "nppa"
    CONSUMER = "consumer"
    NONE = "none"


class BBox(BaseModel):
    page: int
    x0: float
    y0: float
    x1: float
    y1: float


class Evidence(BaseModel):
    """Where a figure comes from. Exactly one kind is filled in."""
    bill_tokens: list[str] = Field(default_factory=list)   # OCR word ids on the bill
    bbox: Optional[BBox] = None
    rule_row: Optional[str] = None                         # reference table row id
    source_id: Optional[str] = None                        # id in data/sources.yaml
    source_ref: Optional[str] = None                       # page / row / clause text
    formula: Optional[str] = None
    inputs: list[str] = Field(default_factory=list)        # input figure ids
    note: Optional[str] = None


class Figure(BaseModel):
    id: str
    value: Decimal
    unit: str              # "INR", "count", "percent", "days"
    role: Role
    origin: Origin
    evidence: Evidence
    confidence: float = 1.0


class Word(BaseModel):
    id: str
    text: str
    bbox: BBox
    conf: float = 1.0


class BillLine(BaseModel):
    id: str
    section: Optional[str] = None          # pharmacy, consumables, implant, room, procedure...
    description: str
    item_date: Optional[date] = None
    batch: Optional[str] = None
    expiry: Optional[str] = None
    qty_fig: Optional[str] = None           # figure ids
    rate_fig: Optional[str] = None
    mrp_fig: Optional[str] = None
    gst_rate_fig: Optional[str] = None
    gst_amount_fig: Optional[str] = None
    amount_fig: Optional[str] = None
    word_ids: list[str] = Field(default_factory=list)
    bbox: Optional[BBox] = None
    flags: list[str] = Field(default_factory=list)   # e.g. "low_ocr_confidence", "arith_mismatch"
    confirmed: bool = False


class BillHeader(BaseModel):
    hospital_name: Optional[str] = None
    hospital_address: Optional[str] = None
    gstin: Optional[str] = None
    registration_no: Optional[str] = None
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None
    bill_type: Optional[str] = None          # "interim" or "final"
    scheme_markers: list[str] = Field(default_factory=list)   # e.g. "PMJAY", "pre-auth no"
    total_fig: Optional[str] = None


class Bill(BaseModel):
    id: str
    pages: int = 1
    words: list[Word] = Field(default_factory=list)
    header: BillHeader = Field(default_factory=BillHeader)
    lines: list[BillLine] = Field(default_factory=list)
    itemised: bool = True
    source_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)   # e.g. "blurry", "removed_injected_text"


class Payer(str, Enum):
    PMJAY = "pmjay"
    STATE_SCHEME = "state_scheme"
    CGHS = "cghs"
    PRIVATE_INSURANCE = "private_insurance"
    CASH = "cash"
    UNKNOWN = "unknown"


class Fact(BaseModel):
    """A context fact with where it came from. value None means unknown."""
    value: Optional[object] = None
    source: str = "unknown"       # "bill", "user", "registry", "empanelment_list"
    note: Optional[str] = None

    @property
    def known(self) -> bool:
        return self.value is not None


class Context(BaseModel):
    state: Fact = Field(default_factory=Fact)
    hospital_id: Fact = Field(default_factory=Fact)
    hospital_empanelled_on_service_date: Fact = Field(default_factory=Fact)
    payer: Fact = Field(default_factory=Fact)
    scheme_booked: Fact = Field(default_factory=Fact)        # was the case booked under the scheme
    scheme_limit_exhausted: Fact = Field(default_factory=Fact)
    service_date: Fact = Field(default_factory=Fact)
    city_tier: Fact = Field(default_factory=Fact)
    package_code: Fact = Field(default_factory=Fact)
    language: str = "en"


class Finding(BaseModel):
    rule_id: str
    family: str
    verdict: Verdict
    line_id: Optional[str] = None
    channel: Channel = Channel.NONE
    message_key: str
    slots: dict[str, str] = Field(default_factory=dict)      # slot name -> figure id
    text_slots: dict[str, str] = Field(default_factory=dict) # slot name -> plain text (names, dates)
    excess_fig: Optional[str] = None                          # recoverable amount for red findings
    legal_status: str = "in_force"
    source_ids: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)       # message keys of conditions to show
    asks: list[str] = Field(default_factory=list)             # message keys of things to request


class AuditResult(BaseModel):
    bill: Bill
    context: Context
    findings: list[Finding]
    figures: dict[str, Figure]
    recoverable_fig: Optional[str] = None      # total that binding rules let the family challenge
    hospital_fig: Optional[str] = None         # part above price caps / wrong arithmetic: ask the hospital
    scheme_fig: Optional[str] = None           # part covered by the scheme: a grievance, decided by the scheme
    fallback_fig: Optional[str] = None         # of the scheme part, what price caps alone still cover
    amber_total_fig: Optional[str] = None
    crosswalk: dict = Field(default_factory=dict)   # line id -> how the line was matched to rules
    coverage: dict = Field(default_factory=dict)    # counts and share of the bill matched to a rule
    data_versions: dict[str, str] = Field(default_factory=dict)
