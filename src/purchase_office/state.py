"""Typed state for the Purchase Office Case File."""

from typing import Literal

from pydantic import BaseModel, Field


class PurchaseRequest(BaseModel):
    item: str
    quantity: int
    reason: str


class Verdict(BaseModel):
    role: str
    decision: Literal["approve", "reject"]
    note: str = ""


class WriteUp(BaseModel):
    screen: str
    detail: str
    source_role: str


class CaseFile(BaseModel):
    request_id: str
    request: PurchaseRequest
    status: str = "RAISED"
    route: list[str] = Field(default_factory=list)
    verdicts: dict[str, Verdict] = Field(default_factory=dict)
    writeups: list[WriteUp] = Field(default_factory=list)
