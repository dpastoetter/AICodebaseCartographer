import { useEffect, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
import type { ScanStatus } from "../types";

const LLMS = [
  { id: "none", label: "Static only (no API key)" },
  { id: "anthropic", label: "Anthropic Claude" },
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
      setError("Please enter a path.");
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
      <div className="panel w-full max-w-3xl p-8 grid gap-8 md:grid-cols-2">
        <div>
          <div className="text-3xl mb-2">🗺️</div>
          <h2 className="text-xl font-semibold">Scan a project</h2>
          <p className="mt-1 text-sm text-slate-400">
            Point at a folder. We map its shape, dependencies, symbols, and
            (optionally) write AI summaries for every module.
          </p>
          <div className="mt-6 space-y-3">
            <label className="block">
              <span className="text-xs uppercase tracking-widest text-slate-500">
                Project path
              </span>
              <input
                className="input mt-1"
                placeholder="/absolute/path/to/repo"
                value={path}
                onChange={(e) => setPath(e.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-widest text-slate-500">
                LLM provider
              </span>
              <select
                className="input mt-1"
                value={llm}
                onChange={(e) => setLlm(e.target.value)}
              >
                {LLMS.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
                  </option>
                ))}
              </select>
            </label>
            {llm !== "none" && (
              <label className="block">
                <span className="text-xs uppercase tracking-widest text-slate-500">
                  Model (optional)
                </span>
                <input
                  className="input mt-1"
                  placeholder="leave blank for default"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                />
              </label>
            )}
            {error && <div className="text-xs text-rose-400">{error}</div>}
            <button className="button" disabled={busy} onClick={start}>
              {busy ? "Starting…" : "Start scan"}
            </button>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-2">
            Recent scans
          </h3>
          {recents.length === 0 ? (
            <div className="text-xs text-slate-500">
              No scans yet. Run one and it'll show up here.
            </div>
          ) : (
            <ul className="space-y-2 max-h-80 overflow-y-auto pr-1">
              {recents
                .slice()
                .sort((a, b) => b.started_at.localeCompare(a.started_at))
                .map((s) => (
                  <li key={s.scan_id}>
                    <button
                      onClick={() => pickRecent(s.scan_id)}
                      className="w-full text-left rounded-lg border border-white/5 bg-canvas-700/50 hover:bg-canvas-700 px-3 py-2 transition"
                    >
                      <div className="font-medium text-sm truncate">
                        {s.root_path.split("/").pop() || s.root_path}
                      </div>
                      <div className="text-[11px] text-slate-500 truncate">
                        {s.root_path}
                      </div>
                      <div className="mt-1 flex items-center gap-1.5">
                        <span className="pill capitalize">{s.state}</span>
                        <span className="pill">{s.totals.files} files</span>
                        {s.llm.kind !== "none" && (
                          <span className="pill">LLM: {s.llm.kind}</span>
                        )}
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
