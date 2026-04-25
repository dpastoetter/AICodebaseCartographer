"""Pydantic models shared between the scanner, the API, and the UI."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

LLMKind = Literal["none", "anthropic", "openai", "ollama"]
ScanState = Literal["queued", "scanning", "analyzing", "summarizing", "done", "error"]
SymbolKind = Literal["function", "method", "class", "interface", "type", "variable"]


class ScanRequest(BaseModel):
    path: str
    llm: LLMKind = "none"
    model: str | None = None
    max_files: int | None = Field(default=None, ge=1)


class ScanProgress(BaseModel):
    files_seen: int = 0
    files_parsed: int = 0
    cards_total: int = 0
    cards_done: int = 0
    message: str = ""


class ScanTotals(BaseModel):
    files: int = 0
    dirs: int = 0
    lines: int = 0
    languages: int = 0
    errors: int = 0


class LLMInfo(BaseModel):
    kind: LLMKind = "none"
    model: str | None = None


class ScanStatus(BaseModel):
    scan_id: str
    root_path: str
    state: ScanState
    started_at: datetime
    finished_at: datetime | None = None
    totals: ScanTotals = Field(default_factory=ScanTotals)
    progress: ScanProgress = Field(default_factory=ScanProgress)
    llm: LLMInfo = Field(default_factory=LLMInfo)
    error: str | None = None


class FileNode(BaseModel):
    path: str
    name: str
    is_dir: bool
    size: int = 0
    lines: int = 0
    language: str | None = None
    children: list[FileNode] = Field(default_factory=list)


class TreeResponse(BaseModel):
    root: FileNode


class DepNode(BaseModel):
    id: str
    label: str
    language: str | None = None
    lines: int = 0
    group: str | None = None


class DepEdge(BaseModel):
    source: str
    target: str
    kind: str = "import"


class DependencyGraph(BaseModel):
    nodes: list[DepNode] = Field(default_factory=list)
    edges: list[DepEdge] = Field(default_factory=list)


class Symbol(BaseModel):
    id: str
    name: str
    kind: SymbolKind
    file: str
    line: int
    parent: str | None = None


class SymbolEdge(BaseModel):
    source: str
    target: str
    kind: str = "calls"


class SymbolGraph(BaseModel):
    nodes: list[Symbol] = Field(default_factory=list)
    edges: list[SymbolEdge] = Field(default_factory=list)


class LanguageStat(BaseModel):
    name: str
    files: int
    lines: int


class TechItem(BaseModel):
    name: str
    kind: Literal["language", "framework", "library", "runtime", "tool"]
    version: str | None = None
    source: str
    category: str | None = None


class TechRadar(BaseModel):
    languages: list[LanguageStat] = Field(default_factory=list)
    items: list[TechItem] = Field(default_factory=list)


class HotspotEntry(BaseModel):
    path: str
    lines: int = 0
    fan_in: int = 0
    fan_out: int = 0
    complexity: int = 0
    churn: int | None = None


class Hotspots(BaseModel):
    largest: list[HotspotEntry] = Field(default_factory=list)
    most_imported: list[HotspotEntry] = Field(default_factory=list)
    most_complex: list[HotspotEntry] = Field(default_factory=list)
    churn: list[HotspotEntry] = Field(default_factory=list)


class ModuleCard(BaseModel):
    path: str
    summary: str
    responsibilities: list[str] = Field(default_factory=list)
    key_symbols: list[str] = Field(default_factory=list)
    tech: list[str] = Field(default_factory=list)
    status: Literal["pending", "ready", "error", "skipped"] = "pending"
    error: str | None = None
