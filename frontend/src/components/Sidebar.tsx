import type { ComponentType } from "react";
import { useStore, type ViewKey } from "../store";
import {
  IconDependencies,
  IconDocument,
  IconHotspots,
  IconMindmap,
  IconModuleCards,
  IconRisks,
  IconSymbols,
  IconTechRadar,
  LogoMark,
} from "./Icons";

const VIEWS: {
  id: ViewKey;
  label: string;
  hint: string;
  Icon: ComponentType<{ className?: string }>;
}[] = [
  { id: "overview", label: "Overview", hint: "Architecture brief", Icon: IconDocument },
  { id: "ask", label: "Ask", hint: "Grounded Q&A", Icon: IconModuleCards },
  { id: "architecture", label: "Architecture", hint: "Layer map", Icon: IconDependencies },
  { id: "mindmap", label: "Structure", hint: "Repository tree", Icon: IconMindmap },
  { id: "deps", label: "Dependencies", hint: "Import graph", Icon: IconDependencies },
  { id: "symbols", label: "Symbols", hint: "Definitions & calls", Icon: IconSymbols },
  { id: "cards", label: "Summaries", hint: "LLM module cards", Icon: IconModuleCards },
  { id: "tech", label: "Technology", hint: "Languages & manifests", Icon: IconTechRadar },
  { id: "hotspots", label: "Hotspots", hint: "Size & coupling", Icon: IconHotspots },
  { id: "risks", label: "Risks", hint: "Vulnerabilities & danger", Icon: IconRisks },
  { id: "changes", label: "Changes", hint: "Compare two scans", Icon: IconDependencies },
];

export function Sidebar() {
  const view = useStore((s) => s.view);
  const status = useStore((s) => s.status);
  const setView = useStore((s) => s.setView);

  return (
    <aside className="flex w-56 shrink-0 flex-col gap-6 border-r border-white/[0.06] bg-canvas-900/95 p-3">
      <div className="flex items-center gap-2.5 px-1">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-white/[0.08] bg-canvas-800 text-accent">
          <LogoMark className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold tracking-tight text-slate-100">
            AICodeCartographer
          </div>
          <div className="text-[11px] text-slate-500">Static analysis &amp; LLM</div>
        </div>
      </div>

      <nav className="flex flex-col gap-0.5">
        {VIEWS.map((v) => {
          const active = view === v.id;
          return (
            <button
              key={v.id}
              type="button"
              onClick={() => setView(v.id)}
              className={`nav-link ${active ? "active" : ""}`}
            >
              <v.Icon className={`h-5 w-5 shrink-0 ${active ? "text-accent" : "text-slate-500"}`} />
              <span className="min-w-0 flex-1">
                <div
                  className={`font-medium leading-tight ${active ? "text-slate-100" : "text-slate-400"}`}
                >
                  {v.label}
                </div>
                <div className="text-[11px] leading-snug text-slate-500">{v.hint}</div>
              </span>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto panel p-3 text-xs">
        {status ? (
          <>
            <div className="font-medium text-slate-300" title={status.root_path}>
              {status.root_path.split("/").pop() || status.root_path}
            </div>
            <div className="mt-1 break-all font-mono text-[11px] leading-relaxed text-slate-500">
              {status.root_path}
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              <span className="pill">{status.totals.files} files</span>
              <span className="pill">{status.totals.dirs} dirs</span>
              <span className="pill">{status.totals.lines} lines</span>
              <span className="pill">{status.llm.kind === "none" ? "LLM off" : status.llm.kind}</span>
            </div>
          </>
        ) : (
          <div className="text-slate-500">No scan loaded.</div>
        )}
      </div>
    </aside>
  );
}
