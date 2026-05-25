import { useEffect, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
import type { ScanStatus } from "../types";

export function Changes() {
  const compare = useStore((s) => s.compare);
  const compareBusy = useStore((s) => s.compareBusy);
  const reviewSummary = useStore((s) => s.reviewSummary);
  const loadCompare = useStore((s) => s.loadCompare);
  const runReview = useStore((s) => s.runReview);
  const scanId = useStore((s) => s.scanId);
  const status = useStore((s) => s.status);

  const [recents, setRecents] = useState<ScanStatus[]>([]);
  const [scanA, setScanA] = useState(scanId ?? "");
  const [scanB, setScanB] = useState("");
  const [reviewRepo, setReviewRepo] = useState("");
  const [reviewBase, setReviewBase] = useState("main");
  const [reviewHead, setReviewHead] = useState("HEAD");
  const [reviewError, setReviewError] = useState<string | null>(null);

  useEffect(() => {
    api.listScans().then(setRecents).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (scanId) setScanA(scanId);
  }, [scanId]);

  return (
    <div className="h-full overflow-y-auto p-6">
      <section className="panel mb-4 p-4">
        <div className="text-sm font-semibold text-slate-200">PR review (git refs)</div>
        <p className="mt-1 text-xs text-slate-500">
          Scan <span className="font-mono">base</span> vs <span className="font-mono">head</span> and open
          the diff automatically. Use a local repo path or GitHub <span className="font-mono">owner/repo</span>.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <input
            className="input font-mono text-xs sm:col-span-3"
            placeholder={status?.root_path || "Repo path or owner/repo"}
            value={reviewRepo}
            onChange={(e) => setReviewRepo(e.target.value)}
          />
          <input
            className="input font-mono text-xs"
            placeholder="base (main)"
            value={reviewBase}
            onChange={(e) => setReviewBase(e.target.value)}
          />
          <input
            className="input font-mono text-xs"
            placeholder="head (feature branch)"
            value={reviewHead}
            onChange={(e) => setReviewHead(e.target.value)}
          />
          <button
            type="button"
            className="button"
            disabled={compareBusy || !reviewRepo.trim()}
            onClick={async () => {
              setReviewError(null);
              try {
                await runReview(reviewRepo.trim(), reviewBase.trim() || "main", reviewHead.trim() || "HEAD");
              } catch (err) {
                setReviewError(err instanceof Error ? err.message : String(err));
              }
            }}
          >
            {compareBusy ? "Scanning refs…" : "Review"}
          </button>
        </div>
        {reviewError && <p className="mt-2 text-xs text-rose-300">{reviewError}</p>}
        {reviewSummary && (
          <p className="mt-3 rounded border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-200">
            {reviewSummary}
          </p>
        )}
      </section>

      <section className="panel mb-4 p-4">
        <div className="text-sm font-semibold text-slate-200">Compare scans</div>
        <p className="mt-1 text-xs text-slate-500">
          Diff files, dependencies, risks, and vulnerabilities between two saved analyses.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="label-upper">Scan A</span>
            <select className="input mt-1.5 font-mono text-xs" value={scanA} onChange={(e) => setScanA(e.target.value)}>
              <option value="">Select…</option>
              {recents.map((s) => (
                <option key={s.scan_id} value={s.scan_id}>
                  {s.scan_id.slice(0, 8)} — {s.root_path.split("/").pop()}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="label-upper">Scan B</span>
            <select className="input mt-1.5 font-mono text-xs" value={scanB} onChange={(e) => setScanB(e.target.value)}>
              <option value="">Select…</option>
              {recents.map((s) => (
                <option key={s.scan_id} value={s.scan_id}>
                  {s.scan_id.slice(0, 8)} — {s.root_path.split("/").pop()}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button
          type="button"
          className="button mt-3"
          disabled={compareBusy || !scanA || !scanB || scanA === scanB}
          onClick={() => loadCompare(scanA, scanB)}
        >
          {compareBusy ? "Comparing…" : "Compare"}
        </button>
      </section>

      {!compare && !compareBusy && (
        <div className="panel p-6 text-sm text-slate-500">Select two scans to see changes.</div>
      )}

      {compare && (
        <div className="grid gap-4 lg:grid-cols-2">
          <DiffList title="Files added" items={compare.files_added} />
          <DiffList title="Files removed" items={compare.files_removed} />
          <DiffList title="Dependencies added" items={compare.deps_added} />
          <DiffList title="Dependencies removed" items={compare.deps_removed} />
          <DiffList title="Risks added" items={compare.risks_added} />
          <DiffList title="Risks removed" items={compare.risks_removed} />
          <DiffList title="Vulnerabilities added" items={compare.vulns_added} />
          <DiffList title="Vulnerabilities removed" items={compare.vulns_removed} />
          {compare.line_deltas.length > 0 && (
            <section className="panel p-4 lg:col-span-2">
              <div className="label-upper mb-2">Line count changes</div>
              <ul className="max-h-48 space-y-1 overflow-y-auto font-mono text-xs text-slate-400">
                {compare.line_deltas.map((d) => (
                  <li key={d.path}>
                    {d.path}: {d.lines_a} → {d.lines_b} ({d.delta >= 0 ? "+" : ""}
                    {d.delta})
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

function DiffList({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="panel p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="label-upper">{title}</div>
        <span className="pill">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <div className="text-xs text-slate-600">None</div>
      ) : (
        <ul className="max-h-40 space-y-1 overflow-y-auto font-mono text-[11px] text-slate-400">
          {items.map((x) => (
            <li key={x} className="break-all">
              {x}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
