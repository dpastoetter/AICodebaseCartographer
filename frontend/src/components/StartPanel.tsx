import { useEffect, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
import type { ScanStatus } from "../types";
import { LogoMark } from "./Icons";

const LLMS = [
  { id: "none", label: "Disabled (static analysis only)" },
  { id: "anthropic", label: "Anthropic" },
  { id: "openai", label: "OpenAI" },
  { id: "ollama", label: "Ollama (local)" },
];

export function StartPanel() {
  const [path, setPath] = useState("");
  const [llm, setLlm] = useState("none");
  const [model, setModel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [recents, setRecents] = useState<ScanStatus[]>([]);
  const attach = useStore((s) => s.attachToScan);

  useEffect(() => {
    api.listScans().then(setRecents).catch(() => undefined);
  }, []);

  async function start() {
    if (!path.trim()) {
      setError("Enter an absolute path to a directory.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const status = await api.startScan({
        path: path.trim(),
        llm,
        model: model.trim() || null,
      });
      const url = new URL(window.location.href);
      url.searchParams.set("scan", status.scan_id);
      window.history.replaceState({}, "", url);
      await attach(status.scan_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function pickRecent(id: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("scan", id);
    window.history.replaceState({}, "", url);
    attach(id).catch(console.error);
  }

  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="panel grid w-full max-w-3xl gap-0 overflow-hidden md:grid-cols-2">
        <div className="border-b border-white/[0.06] p-7 md:border-b-0 md:border-r">
          <div className="mb-5 flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md border border-white/[0.08] bg-canvas-800 text-accent">
              <LogoMark className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">New analysis</h2>
              <p className="text-xs text-slate-500">Tree-sitter parse, graphs, optional LLM cards</p>
            </div>
          </div>
          <div className="space-y-4">
            <label className="block">
              <span className="label-upper">Repository path</span>
              <input
                className="input mt-1.5 font-mono text-xs"
                placeholder="/absolute/path/to/repository"
                value={path}
                onChange={(e) => setPath(e.target.value)}
              />
            </label>
            <label className="block">
              <span className="label-upper">LLM provider</span>
              <select className="input mt-1.5" value={llm} onChange={(e) => setLlm(e.target.value)}>
                {LLMS.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
                  </option>
                ))}
              </select>
            </label>
            {llm !== "none" && (
              <label className="block">
                <span className="label-upper">Model override</span>
                <input
                  className="input mt-1.5 font-mono text-xs"
                  placeholder="Optional — provider default if empty"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                />
              </label>
            )}
            {error && <div className="text-xs text-rose-400">{error}</div>}
            <button type="button" className="button w-full sm:w-auto" disabled={busy} onClick={start}>
              {busy ? "Starting…" : "Run analysis"}
            </button>
          </div>
        </div>

        <div className="p-7">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Recent analyses
          </h3>
          {recents.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">No saved scans on this machine yet.</p>
          ) : (
            <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto pr-1">
              {recents
                .slice()
                .sort((a, b) => b.started_at.localeCompare(a.started_at))
                .map((s) => (
                  <li key={s.scan_id}>
                    <button
                      type="button"
                      onClick={() => pickRecent(s.scan_id)}
                      className="w-full rounded-md border border-white/[0.06] bg-canvas-900/50 px-3 py-2.5 text-left transition hover:border-white/[0.1] hover:bg-canvas-700/40"
                    >
                      <div className="truncate text-sm font-medium text-slate-200">
                        {s.root_path.split("/").pop() || s.root_path}
                      </div>
                      <div className="truncate font-mono text-[11px] text-slate-500">{s.root_path}</div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        <span className="pill">{s.state}</span>
                        <span className="pill">{s.totals.files} files</span>
                        {s.llm.kind !== "none" && <span className="pill">{s.llm.kind}</span>}
                      </div>
                    </button>
                  </li>
                ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
