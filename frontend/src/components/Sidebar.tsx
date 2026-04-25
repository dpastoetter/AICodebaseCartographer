import { useStore, type ViewKey } from "../store";

const VIEWS: { id: ViewKey; label: string; icon: string; hint: string }[] = [
  { id: "mindmap", label: "Mindmap", icon: "🗺️", hint: "Project shape" },
  { id: "deps", label: "Dependencies", icon: "🔗", hint: "Module graph" },
  { id: "symbols", label: "Symbols", icon: "⚛️", hint: "Calls & classes" },
  { id: "cards", label: "Module cards", icon: "📇", hint: "AI summaries" },
  { id: "tech", label: "Tech radar", icon: "📡", hint: "Languages & libs" },
  { id: "hotspots", label: "Hotspots", icon: "🔥", hint: "Big & busy files" },
];

export function Sidebar() {
  const view = useStore((s) => s.view);
  const status = useStore((s) => s.status);
  const setView = useStore((s) => s.setView);

  return (
    <aside className="w-64 shrink-0 border-r border-white/5 bg-canvas-900/80 p-4 flex flex-col gap-6">
      <div>
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-accent/20 text-accent">
            <span>🗺</span>
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">
              AICodeCartographer
            </div>
            <div className="text-[10px] uppercase tracking-widest text-slate-500">
              v0.1.0
            </div>
          </div>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            onClick={() => setView(v.id)}
            className={`nav-link ${view === v.id ? "active" : ""}`}
          >
            <span className="text-base">{v.icon}</span>
            <span className="flex-1 text-left">
              <div className="text-sm font-medium">{v.label}</div>
              <div className="text-[11px] text-slate-500">{v.hint}</div>
            </span>
          </button>
        ))}
      </nav>

      <div className="mt-auto panel p-3 text-xs">
        {status ? (
          <>
            <div className="font-semibold text-slate-200 truncate" title={status.root_path}>
              {status.root_path.split("/").pop() || status.root_path}
            </div>
            <div className="mt-1 text-slate-400 break-all">{status.root_path}</div>
            <div className="mt-2 flex flex-wrap gap-1">
              <span className="pill">{status.totals.files} files</span>
              <span className="pill">{status.totals.dirs} dirs</span>
              <span className="pill">{status.totals.lines} lines</span>
              <span className="pill">LLM: {status.llm.kind}</span>
            </div>
          </>
        ) : (
          <div className="text-slate-500">No active scan.</div>
        )}
      </div>
    </aside>
  );
}
