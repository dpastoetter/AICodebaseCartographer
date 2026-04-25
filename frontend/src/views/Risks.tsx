import { useMemo, useState } from "react";
import { useStore } from "../store";
import type { RiskFinding, RiskSeverity } from "../types";

const SEV_ORDER: Record<RiskSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
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

export function Risks() {
  const report = useStore((s) => s.risks);
  const setSelected = useStore((s) => s.setSelected);
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
                Heuristic checks for secrets, dangerous APIs, and insecure configuration.
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(["critical", "high", "medium", "low"] as const).map((s) => (
                <span key={s} className={`pill ${badgeClass(s)}`}>
                  {s}: {counts[s]}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="panel p-4">
          <div className="label-upper mb-2">Filters</div>
          <div className="flex flex-col gap-2">
            <input
              className="input"
              placeholder="Search title, path, rule…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-2">
              <select
                className="input"
                value={sev}
                onChange={(e) => setSev(e.target.value as any)}
              >
                <option value="all">All severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="all">All kinds</option>
                {kinds.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </div>
            <div className="font-mono text-[11px] text-slate-500">
              {filtered.length} / {findings.length} findings
            </div>
          </div>
        </section>
      </div>

      {findings.length === 0 ? (
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
              {filtered.map((f) => (
                <Row key={f.id} f={f} onOpen={() => f.path && setSelected(f.path)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
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

