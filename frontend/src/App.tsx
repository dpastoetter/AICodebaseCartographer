import { useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { ScanProgress } from "./components/ScanProgress";
import { DetailPanel } from "./components/DetailPanel";
import { StartPanel } from "./components/StartPanel";
import { Mindmap } from "./views/Mindmap";
import { DependencyGraph } from "./views/DependencyGraph";
import { SymbolGraph } from "./views/SymbolGraph";
import { ModuleCards } from "./views/ModuleCards";
import { TechRadar } from "./views/TechRadar";
import { Hotspots } from "./views/Hotspots";
import { Risks } from "./views/Risks";
import { Overview } from "./views/Overview";
import { Ask } from "./views/Ask";
import { Architecture } from "./views/Architecture";
import { Changes } from "./views/Changes";
import { useStore } from "./store";
import type { ScanState } from "./types";
import { SecretsModal } from "./components/SecretsModal";
import { GlobalSearch, GlobalSearchTrigger } from "./components/GlobalSearch";
import { api } from "./api";

export function App() {
  const view = useStore((s) => s.view);
  const status = useStore((s) => s.status);
  const scanId = useStore((s) => s.scanId);
  const attach = useStore((s) => s.attachToScan);
  const selected = useStore((s) => s.selectedPath);
  const startRepoScan = useStore((s) => s.startRepoScan);
  const watch = useStore((s) => s.watch);
  const setWatch = useStore((s) => s.setWatch);
  const statusState = status?.state;

  const [repo, setRepo] = useState("");
  const [busy, setBusy] = useState(false);
  const [repoError, setRepoError] = useState<string | null>(null);
  const [keysOpen, setKeysOpen] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const scan = params.get("scan");
    if (scan) {
      attach(scan).catch(console.error);
    }
  }, [attach]);

  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="relative flex-1 overflow-hidden">
        <header className="flex items-center justify-between border-b border-white/[0.06] bg-canvas-900/80 px-5 py-2.5 backdrop-blur-sm">
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-slate-100">
              {scanId ? viewLabel(view) : "Overview"}
            </h1>
            <p className="mt-0.5 truncate font-mono text-[11px] text-slate-500">
              {status?.root_path ?? "Select a repository to analyze."}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            <form
              className="flex items-center gap-2"
              onSubmit={async (e) => {
                e.preventDefault();
                const v = normalizeRepoInput(repo.trim());
                if (!v) return;
                setRepoError(null);
                setBusy(true);
                try {
                  await startRepoScan(v);
                  setRepo("");
                } catch (err) {
                  setRepoError(err instanceof Error ? err.message : String(err));
                } finally {
                  setBusy(false);
                }
              }}
            >
              <input
                className="input w-80 font-mono text-xs"
                placeholder="GitHub repo (owner/repo or https://github.com/owner/repo)"
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                disabled={busy}
              />
              <button className="button" type="submit" disabled={busy || !repo.trim()}>
                {busy ? "Cloning…" : "Analyze"}
              </button>
            </form>
            {scanId && statusState === "done" && (
              <button
                type="button"
                className={`button !bg-white/[0.04] text-xs ${watch?.enabled ? "!border-emerald-500/40" : ""}`}
                onClick={() => void setWatch(!watch?.enabled)}
                title={watch?.message || "Live watch mode"}
              >
                {watch?.updating ? "Updating…" : watch?.enabled ? "Watch on" : "Watch"}
              </button>
            )}
            {scanId && <GlobalSearchTrigger />}
            {scanId && (
              <a
                className="button !bg-white/[0.04] font-mono text-xs"
                href={api.exportUrl(scanId, "html")}
                target="_blank"
                rel="noreferrer"
              >
                Export
              </a>
            )}
            <button type="button" className="button !bg-white/[0.04]" onClick={() => setKeysOpen(true)}>
              Keys
            </button>
            {status && (
              <>
                <span className="pill">
                  {status.totals.files} files · {status.totals.languages} langs
                </span>
                <StatusBadge state={status.state} />
              </>
            )}
          </div>
        </header>
        {repoError && (
          <div className="border-b border-white/[0.06] bg-canvas-900/60 px-5 py-2 text-xs text-rose-300">
            {repoError}
          </div>
        )}
        <div className="flex h-[calc(100%-45px)]">
          <section className="relative flex-1 overflow-hidden">
            {!scanId && <StartPanel />}
            {scanId && view === "overview" && <Overview />}
            {scanId && view === "ask" && <Ask />}
            {scanId && view === "architecture" && <Architecture />}
            {scanId && view === "mindmap" && <Mindmap />}
            {scanId && view === "deps" && <DependencyGraph />}
            {scanId && view === "symbols" && <SymbolGraph />}
            {scanId && view === "cards" && <ModuleCards />}
            {scanId && view === "tech" && <TechRadar />}
            {scanId && view === "hotspots" && <Hotspots />}
            {scanId && view === "risks" && <Risks />}
            {scanId && view === "changes" && <Changes />}
            <ScanProgress />
          </section>
          {selected && <DetailPanel />}
        </div>
        <SecretsModal open={keysOpen} onClose={() => setKeysOpen(false)} />
        <GlobalSearch />
      </main>
    </div>
  );
}

function normalizeRepoInput(value: string): string {
  if (/^https?:\/github\.com\//i.test(value) && !/^https?:\/\/github\.com\//i.test(value)) {
    return value.replace(/^https?:\/github\.com\//i, (m) => m.replace(":/", "://"));
  }
  if (/^github\.com\//i.test(value)) return `https://${value}`;
  return value;
}

function StatusBadge({ state }: { state: ScanState }) {
  const styles: Record<ScanState, string> = {
    queued: "border-slate-600/40 bg-slate-500/10 text-slate-400",
    scanning: "border-amber-500/25 bg-amber-500/10 text-amber-200",
    analyzing: "border-amber-500/25 bg-amber-500/10 text-amber-200",
    summarizing: "border-sky-500/25 bg-sky-500/10 text-sky-200",
    done: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300/90",
    error: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  };
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wide ${styles[state]}`}
    >
      {state}
    </span>
  );
}

function viewLabel(v: string): string {
  switch (v) {
    case "overview":
      return "Overview";
    case "ask":
      return "Ask";
    case "architecture":
      return "Architecture";
    case "mindmap":
      return "Structure";
    case "deps":
      return "Dependencies";
    case "symbols":
      return "Symbols";
    case "cards":
      return "Summaries";
    case "tech":
      return "Technology";
    case "hotspots":
      return "Hotspots";
    case "risks":
      return "Risks";
    case "changes":
      return "Changes";
    default:
      return v;
  }
}
