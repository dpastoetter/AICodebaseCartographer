export type LLMKind = "none" | "anthropic" | "openai" | "ollama";

export type ScanState =
  | "queued"
  | "scanning"
  | "analyzing"
  | "summarizing"
  | "done"
  | "error";

export interface ScanProgress {
  files_seen: number;
  files_parsed: number;
  cards_total: number;
  cards_done: number;
  message: string;
}

export interface ScanTotals {
  files: number;
  dirs: number;
  lines: number;
  languages: number;
  errors: number;
}

export interface LLMInfo {
  kind: LLMKind;
  model: string | null;
}

export interface ScanStatus {
  scan_id: string;
  root_path: string;
  state: ScanState;
  started_at: string;
  finished_at: string | null;
  totals: ScanTotals;
  progress: ScanProgress;
  llm: LLMInfo;
  error: string | null;
}

export interface FileNode {
  path: string;
  name: string;
  is_dir: boolean;
  size: number;
  lines: number;
  language: string | null;
  children: FileNode[];
}

export interface TreeResponse {
  root: FileNode;
}

export interface DepNode {
  id: string;
  label: string;
  language: string | null;
  lines: number;
  group: string | null;
}

export interface DepEdge {
  source: string;
  target: string;
  kind: string;
}

export interface DependencyGraph {
  nodes: DepNode[];
  edges: DepEdge[];
}

export type SymbolKind =
  | "function"
  | "method"
  | "class"
  | "interface"
  | "type"
  | "variable";

export interface Symbol {
  id: string;
  name: string;
  kind: SymbolKind;
  file: string;
  line: number;
  parent: string | null;
}

export interface SymbolEdge {
  source: string;
  target: string;
  kind: string;
}

export interface SymbolGraph {
  nodes: Symbol[];
  edges: SymbolEdge[];
}

export interface LanguageStat {
  name: string;
  files: number;
  lines: number;
}

export interface TechItem {
  name: string;
  kind: "language" | "framework" | "library" | "runtime" | "tool";
  version: string | null;
  source: string;
  category: string | null;
}

export interface TechRadar {
  languages: LanguageStat[];
  items: TechItem[];
}

export interface HotspotEntry {
  path: string;
  lines: number;
  fan_in: number;
  fan_out: number;
  complexity: number;
  churn: number | null;
}

export interface Hotspots {
  largest: HotspotEntry[];
  most_imported: HotspotEntry[];
  most_complex: HotspotEntry[];
  churn: HotspotEntry[];
}

export interface ModuleCard {
  path: string;
  summary: string;
  responsibilities: string[];
  key_symbols: string[];
  tech: string[];
  status: "pending" | "ready" | "error" | "skipped";
  error: string | null;
}

export type RiskSeverity = "low" | "medium" | "high" | "critical";
export type RiskKind =
  | "secret"
  | "insecure_api"
  | "insecure_config"
  | "dependency"
  | "note";

export interface RiskFinding {
  id: string;
  severity: RiskSeverity;
  kind: RiskKind;
  title: string;
  detail: string | null;
  remediation: string | null;
  path: string | null;
  line: number | null;
  rule: string | null;
}

export interface RisksReport {
  findings: RiskFinding[];
}

export type VulnSeverity = "unknown" | "low" | "medium" | "high" | "critical";

export interface VulnReference {
  type: string | null;
  url: string;
}

export interface PackageVulnerability {
  vuln_id: string;
  summary: string | null;
  details: string | null;
  severity: VulnSeverity;
  references: VulnReference[];
  fixed: string[];
}

export interface PackageVulns {
  ecosystem: string;
  name: string;
  version: string;
  vulnerabilities: PackageVulnerability[];
}

export interface VulnsReport {
  packages: PackageVulns[];
}

export interface ArchitectureBrief {
  project_name: string;
  purpose: string;
  modules: string;
  tech_stack: string;
  dependency_hubs: string;
  hotspots_note: string;
  top_risks: string[];
  top_vulns: string[];
}

export interface ScanCompareResult {
  scan_a: string;
  scan_b: string;
  files_added: string[];
  files_removed: string[];
  deps_added: string[];
  deps_removed: string[];
  risks_added: string[];
  risks_removed: string[];
  vulns_added: string[];
  vulns_removed: string[];
  line_deltas: Array<{ path: string; lines_a: number; lines_b: number; delta: number }>;
}
