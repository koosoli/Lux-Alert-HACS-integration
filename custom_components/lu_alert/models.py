from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from .enums import (
    Status, MsgType, Scope, Code, Category, Urgency, Severity, Certainty
)

@dataclass
class Parameter:
    valueName: str
    value: str

@dataclass
class Area:
    areaDesc: str
    polygon: Optional[str] = None
    circle: Optional[str] = None
    geocode: Optional[str] = None
    altitude: Optional[float] = None
    ceiling: Optional[float] = None


@dataclass
class Info:
    language: str
    category: List[Category]
    event: str
    urgency: Urgency
    severity: Severity
    certainty: Certainty

    # While the spec allows multiple areas, it recommends one per info.
    # A list is the correct representation.
    area: List[Area] = field(default_factory=list)

    # Optional fields
    responseType: Optional[str] = None
    audience: Optional[str] = None
    effective: Optional[datetime] = None
    onset: Optional[datetime] = None
    expires: Optional[datetime] = None
    senderName: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    instruction: Optional[str] = None
    web: Optional[str] = None
    contact: Optional[str] = None
    parameters: List[Parameter] = field(default_factory=list)


@dataclass
class Alert:
    identifier: str
    sender: str
    sent: datetime
    status: Status
    msgType: MsgType
    scope: Scope

    # Mandatory in CAP-LU, optional in CAP 1.2
    code: List[Code] = field(default_factory=list)

    # Optional fields
    source: Optional[str] = None
    restriction: Optional[str] = None
    addresses: Optional[str] = None
    note: Optional[str] = None
    references: Optional[str] = None
    incidents: Optional[str] = None
    info: List[Info] = field(default_factory=list)
