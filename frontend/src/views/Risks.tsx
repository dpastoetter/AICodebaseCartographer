import { useMemo, useState } from "react";
import { useStore } from "../store";
import type { PackageVulnerability, RiskFinding, RiskSeverity, VulnSeverity, VulnsReport } from "../types";

const SEV_ORDER: Record<RiskSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const VULN_SEV_ORDER: Record<VulnSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  unknown: 4,
};

function badgeClass(sev: RiskSeverity): string {
  switch (sev) {
    case "critical":
      return "border-rose-500/30 bg-rose-500/10 text-rose-300";
    case "high":
      return "border-amber-500/25 bg-amber-500/10 text-amber-200";
    case "medium":
      return "border-sky-500/25 bg-sky-500/10 text-sky-200";
    case "low":
      return "border-slate-600/40 bg-slate-500/10 text-slate-400";
  }
}

function vulnBadgeClass(sev: VulnSeverity): string {
  switch (sev) {
    case "critical":
      return "border-rose-500/30 bg-rose-500/10 text-rose-300";
    case "high":
      return "border-amber-500/25 bg-amber-500/10 text-amber-200";
    case "medium":
      return "border-sky-500/25 bg-sky-500/10 text-sky-200";
    case "low":
      return "border-slate-600/40 bg-slate-500/10 text-slate-400";
    case "unknown":
      return "border-slate-700/40 bg-slate-800/40 text-slate-400";
  }
}

export function Risks() {
  const report = useStore((s) => s.risks);
  const vulns = useStore((s) => s.vulns);
  const setSelected = useStore((s) => s.setSelected);
  const [tab, setTab] = useState<"heuristics" | "vulns">("heuristics");
  const [sev, setSev] = useState<RiskSeverity | "all">("all");
  const [kind, setKind] = useState<string>("all");
  const [q, setQ] = useState("");

  const { findings, kinds } = useMemo(() => {
    const all = report?.findings ?? [];
    const ks = Array.from(new Set(all.map((f) => f.kind))).sort();
    return { findings: all, kinds: ks };
  }, [report]);

  const filtered = useMemo(() => {
    let items = findings.slice();
    if (sev !== "all") items = items.filter((f) => f.severity === sev);
    if (kind !== "all") items = items.filter((f) => f.kind === kind);
    if (q.trim()) {
      const s = q.toLowerCase();
      items = items.filter(
        (f) =>
          f.title.toLowerCase().includes(s) ||
          (f.detail ?? "").toLowerCase().includes(s) ||
          (f.path ?? "").toLowerCase().includes(s) ||
          (f.rule ?? "").toLowerCase().includes(s),
      );
    }
    items.sort(
      (a, b) =>
        SEV_ORDER[a.severity] - SEV_ORDER[b.severity] ||
        (a.path ?? "").localeCompare(b.path ?? "") ||
        (a.line ?? 0) - (b.line ?? 0),
    );
    return items;
  }, [findings, sev, kind, q]);

  if (!report) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        Computing risk report…
      </div>
    );
  }

  const counts = countBySeverity(findings);

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-4 grid gap-3 lg:grid-cols-3">
        <section className="panel p-4 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-200">Risks</div>
              <div className="mt-0.5 text-xs text-slate-500">
                Heuristics and real dependency vulnerabilities (OSV).
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                className={`pill ${tab === "heuristics" ? "border-white/15 bg-white/[0.06] text-slate-200" : "border-white/[0.08] bg-white/[0.03] text-slate-400 hover:text-slate-200"}`}
                onClick={() => setTab("heuristics")}
              >
                Heuristics
              </button>
              <button
                type="button"
                className={`pill ${tab === "vulns" ? "border-white/15 bg-white/[0.06] text-slate-200" : "border-white/[0.08] bg-white/[0.03] text-slate-400 hover:text-slate-200"}`}
                onClick={() => setTab("vulns")}
              >
                Vulnerabilities (OSV)
              </button>
            </div>
          </div>
        </section>

        <section className="panel p-4">
          {tab === "heuristics" ? (
            <HeuristicFilters
              q={q}
              setQ={setQ}
              sev={sev}
              setSev={setSev}
              kind={kind}
              setKind={setKind}
              kinds={kinds}
              filteredCount={filtered.length}
              totalCount={findings.length}
            />
          ) : (
            <VulnSummary vulnsLoaded={!!vulns} />
          )}
        </section>
      </div>

      {tab === "heuristics" ? (
        <HeuristicsTable findings={findings} filtered={filtered} counts={counts} onOpen={setSelected} />
      ) : (
        <VulnsTable vulns={vulns} />
      )}
    </div>
  );
}

function HeuristicFilters(props: {
  q: string;
  setQ: (v: string) => void;
  sev: RiskSeverity | "all";
  setSev: (v: RiskSeverity | "all") => void;
  kind: string;
  setKind: (v: string) => void;
  kinds: string[];
  filteredCount: number;
  totalCount: number;
}) {
  return (
    <>
      <div className="label-upper mb-2">Filters</div>
      <div className="flex flex-col gap-2">
        <input
          className="input"
          placeholder="Search title, path, rule…"
          value={props.q}
          onChange={(e) => props.setQ(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-2">
          <select className="input" value={props.sev} onChange={(e) => props.setSev(e.target.value as any)}>
            <option value="all">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select className="input" value={props.kind} onChange={(e) => props.setKind(e.target.value)}>
            <option value="all">All kinds</option>
            {props.kinds.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>
        <div className="font-mono text-[11px] text-slate-500">
          {props.filteredCount} / {props.totalCount} findings
        </div>
      </div>
    </>
  );
}

function VulnSummary({ vulnsLoaded }: { vulnsLoaded: boolean }) {
  return (
    <>
      <div className="label-upper mb-2">OSV</div>
      <div className="text-xs text-slate-500">
        {vulnsLoaded ? "Loaded from vulns.json." : "Querying OSV… (or no lockfile / pinned deps found)"}
      </div>
    </>
  );
}

function HeuristicsTable(props: {
  findings: RiskFinding[];
  filtered: RiskFinding[];
  counts: Record<RiskSeverity, number>;
  onOpen: (path: string | null) => void;
}) {
  return (
    <>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {(["critical", "high", "medium", "low"] as const).map((s) => (
          <span key={s} className={`pill ${badgeClass(s)}`}>
            {s}: {props.counts[s]}
          </span>
        ))}
      </div>

      {props.findings.length === 0 ? (
        <div className="panel p-6 text-sm text-slate-500">No findings.</div>
      ) : (
        <div className="panel overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-white/[0.06] bg-canvas-900/60">
              <tr className="text-xs text-slate-500">
                <th className="px-4 py-3 font-medium">Severity</th>
                <th className="px-4 py-3 font-medium">Finding</th>
                <th className="px-4 py-3 font-medium">Location</th>
                <th className="px-4 py-3 font-medium">Rule</th>
              </tr>
            </thead>
            <tbody>
              {props.filtered.map((f) => (
                <Row key={f.id} f={f} onOpen={() => f.path && props.onOpen(f.path)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Row({ f, onOpen }: { f: RiskFinding; onOpen: () => void }) {
  return (
    <tr className="border-b border-white/[0.06] hover:bg-white/[0.02]">
      <td className="px-4 py-3 align-top">
        <span
          className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wide ${badgeClass(f.severity)}`}
        >
          {f.severity}
        </span>
      </td>
      <td className="px-4 py-3 align-top">
        <div className="font-medium text-slate-200">{f.title}</div>
        {f.detail && <div className="mt-1 text-xs text-slate-500">{f.detail}</div>}
        {f.remediation && (
          <div className="mt-1 text-xs text-emerald-300/80">Fix: {f.remediation}</div>
        )}
      </td>
      <td className="px-4 py-3 align-top">
        {f.path ? (
          <button type="button" className="text-left" onClick={onOpen}>
            <div className="font-mono text-[11px] text-accent hover:underline">{f.path}</div>
            {typeof f.line === "number" && (
              <div className="font-mono text-[11px] text-slate-500">line {f.line}</div>
            )}
          </button>
        ) : (
          <div className="font-mono text-[11px] text-slate-500">—</div>
        )}
      </td>
      <td className="px-4 py-3 align-top">
        <div className="font-mono text-[11px] text-slate-500">{f.rule ?? "—"}</div>
        <div className="mt-1 font-mono text-[11px] text-slate-600">{f.kind}</div>
      </td>
    </tr>
  );
}

function countBySeverity(findings: RiskFinding[]): Record<RiskSeverity, number> {
  const out: Record<RiskSeverity, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const f of findings) out[f.severity] += 1;
  return out;
}

function VulnsTable({ vulns }: { vulns: VulnsReport | null }) {
  const [vSev, setVSev] = useState<VulnSeverity | "all">("all");
  const [eco, setEco] = useState("all");
  const [pkgQ, setPkgQ] = useState("");

  const allRows = useMemo(() => {
    const items: Array<{
      ecosystem: string;
      name: string;
      version: string;
      v: PackageVulnerability;
    }> = [];
    const pkgs = vulns?.packages ?? [];
    for (const p of pkgs) {
      for (const v of p.vulnerabilities ?? []) {
        items.push({ ecosystem: p.ecosystem, name: p.name, version: p.version, v });
      }
    }
    items.sort(
      (a, b) =>
        VULN_SEV_ORDER[(a.v.severity ?? "unknown") as VulnSeverity] -
          VULN_SEV_ORDER[(b.v.severity ?? "unknown") as VulnSeverity] ||
        a.name.localeCompare(b.name) ||
        String(a.v.vuln_id).localeCompare(String(b.v.vuln_id)),
    );
    return items;
  }, [vulns]);

  const ecosystems = useMemo(
    () => Array.from(new Set(allRows.map((r) => r.ecosystem))).sort(),
    [allRows],
  );

  const rows = useMemo(() => {
    let items = allRows;
    if (vSev !== "all") items = items.filter((r) => (r.v.severity ?? "unknown") === vSev);
    if (eco !== "all") items = items.filter((r) => r.ecosystem === eco);
    if (pkgQ.trim()) {
      const s = pkgQ.toLowerCase();
      items = items.filter(
        (r) =>
          r.name.toLowerCase().includes(s) ||
          r.v.vuln_id.toLowerCase().includes(s) ||
          (r.v.summary ?? "").toLowerCase().includes(s),
      );
    }
    return items;
  }, [allRows, vSev, eco, pkgQ]);

  if (!vulns) {
    return (
      <div className="panel p-6 text-sm text-slate-500">
        No vulnerability report yet (still scanning or no lockfile / pinned dependencies).
      </div>
    );
  }

  if (allRows.length === 0) {
    return <div className="panel p-6 text-sm text-slate-500">No vulnerabilities found.</div>;
  }

  return (
    <>
      <section className="panel mb-3 p-4">
        <div className="label-upper mb-2">Filters</div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input flex-1 font-mono text-xs"
            placeholder="Search package or CVE…"
            value={pkgQ}
            onChange={(e) => setPkgQ(e.target.value)}
          />
          <select className="input w-full sm:w-36" value={vSev} onChange={(e) => setVSev(e.target.value as VulnSeverity | "all")}>
            <option value="all">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="unknown">Unknown</option>
          </select>
          <select className="input w-full sm:w-28" value={eco} onChange={(e) => setEco(e.target.value)}>
            <option value="all">All ecosystems</option>
            {ecosystems.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>
        <div className="mt-2 font-mono text-[11px] text-slate-500">
          {rows.length} / {allRows.length} vulnerabilities
        </div>
      </section>
    <div className="panel overflow-hidden">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-white/[0.06] bg-canvas-900/60">
          <tr className="text-xs text-slate-500">
            <th className="px-4 py-3 font-medium">Severity</th>
            <th className="px-4 py-3 font-medium">Package</th>
            <th className="px-4 py-3 font-medium">Vulnerability</th>
            <th className="px-4 py-3 font-medium">Fix</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.name}@${r.version}:${r.v.vuln_id}`} className="border-b border-white/[0.06] hover:bg-white/[0.02]">
              <td className="px-4 py-3 align-top">
                <span
                  className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wide ${vulnBadgeClass((r.v.severity ?? "unknown") as VulnSeverity)}`}
                >
                  {(r.v.severity ?? "unknown") as string}
                </span>
              </td>
              <td className="px-4 py-3 align-top">
                <div className="font-mono text-[12px] text-slate-200">
                  {r.name}@{r.version}
                </div>
                <div className="mt-1 text-xs text-slate-500">{r.ecosystem}</div>
              </td>
              <td className="px-4 py-3 align-top">
                <div className="font-mono text-[12px] text-slate-200">{r.v.vuln_id}</div>
                {r.v.summary && <div className="mt-1 text-xs text-slate-500">{r.v.summary}</div>}
                {(r.v.references ?? []).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(r.v.references ?? []).slice(0, 2).map((ref) => (
                      <a
                        key={ref.url}
                        href={ref.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-mono text-[11px] text-accent hover:underline"
                      >
                        link
                      </a>
                    ))}
                  </div>
                )}
              </td>
              <td className="px-4 py-3 align-top">
                {(r.v.fixed ?? []).length > 0 ? (
                  <div className="font-mono text-[11px] text-slate-500">{r.v.fixed[0]}</div>
                ) : (
                  <div className="font-mono text-[11px] text-slate-600">—</div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    </>
  );
}

