import type {
  ArchitectureBrief,
  DependencyGraph,
  Hotspots,
  ModuleCard,
  RisksReport,
  ScanCompareResult,
  VulnsReport,
  ScanStatus,
  SymbolGraph,
  TechRadar,
  TreeResponse,
} from "./types";

const API_BASE = "";

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) {
    throw new Error(`${r.status} ${r.statusText} for ${path}`);
  }
  return (await r.json()) as T;
}

export const api = {
  health: () => getJSON<{ status: string }>("/api/health"),
  listScans: () => getJSON<ScanStatus[]>("/api/scans"),
  getScan: (id: string) => getJSON<ScanStatus>(`/api/scans/${id}`),
  startScan: async (body: {
    path: string;
    llm: string;
    model?: string | null;
    max_files?: number | null;
  }): Promise<ScanStatus> => {
    const r = await fetch(`${API_BASE}/api/scans`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  startScanFromRepo: async (body: {
    repo: string;
    llm: string;
    model?: string | null;
    max_files?: number | null;
  }): Promise<ScanStatus> => {
    const r = await fetch(`${API_BASE}/api/scans/from-repo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  tree: (id: string) => getJSON<TreeResponse>(`/api/scans/${id}/tree`),
  deps: (id: string) => getJSON<DependencyGraph>(`/api/scans/${id}/dependencies`),
  symbols: (id: string) => getJSON<SymbolGraph>(`/api/scans/${id}/symbols`),
  tech: (id: string) => getJSON<TechRadar>(`/api/scans/${id}/tech`),
  hotspots: (id: string) => getJSON<Hotspots>(`/api/scans/${id}/hotspots`),
  risks: (id: string) => getJSON<RisksReport>(`/api/scans/${id}/risks`),
  vulns: (id: string) => getJSON<VulnsReport>(`/api/scans/${id}/vulns`),
  brief: (id: string) => getJSON<ArchitectureBrief>(`/api/scans/${id}/brief`),
  compareScans: (a: string, b: string) =>
    getJSON<ScanCompareResult>(`/api/scans/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`),
  exportUrl: (id: string, format: "md" | "html") =>
    `${API_BASE}/api/scans/${id}/export?format=${format}`,
  cards: (id: string) =>
    getJSON<{ cards: ModuleCard[] }>(`/api/scans/${id}/cards`),

  secrets: async (): Promise<Record<string, boolean>> => getJSON(`/api/secrets`),
  setSecret: async (provider: "openai" | "anthropic", api_key: string) => {
    const r = await fetch(`${API_BASE}/api/secrets/${provider}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key }),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json() as Promise<Record<string, boolean>>;
  },
  clearSecret: async (provider: "openai" | "anthropic") => {
    const r = await fetch(`${API_BASE}/api/secrets/${provider}`, { method: "DELETE" });
    if (!r.ok) throw new Error(await r.text());
    return r.json() as Promise<Record<string, boolean>>;
  },
};

export type ScanEvent =
  | { type: "status"; status: ScanStatus }
  | { type: "progress"; progress: ScanStatus["progress"] }
  | { type: "card"; card: ModuleCard };

export function subscribeToScan(
  scanId: string,
  onEvent: (e: ScanEvent) => void,
): () => void {
  const es = new EventSource(`${API_BASE}/api/scans/${scanId}/events`);

  const handler = (kind: ScanEvent["type"]) => (msg: MessageEvent) => {
    try {
      onEvent(JSON.parse(msg.data));
    } catch (err) {
      console.warn(`bad ${kind} event`, err);
    }
  };

  es.addEventListener("status", handler("status"));
  es.addEventListener("progress", handler("progress"));
  es.addEventListener("card", handler("card"));
  es.onerror = () => {
    es.close();
  };

  return () => es.close();
}
