import { useEffect } from "react";
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
import { useStore } from "./store";

export function App() {
  const view = useStore((s) => s.view);
  const status = useStore((s) => s.status);
  const scanId = useStore((s) => s.scanId);
  const attach = useStore((s) => s.attachToScan);
  const selected = useStore((s) => s.selectedPath);

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
        <header className="flex items-center justify-between border-b border-white/5 bg-canvas-900/50 px-6 py-3">
          <div>
            <h1 className="text-base font-semibold capitalize">
              {scanId ? viewLabel(view) : "Welcome"}
            </h1>
            <div className="text-xs text-slate-500">
              {status?.root_path ?? "Pick a project to map."}
            </div>
          </div>
          {status && (
            <div className="flex items-center gap-2">
              <span className="pill">
                {status.totals.files} files · {status.totals.languages} langs
              </span>
              <span className="pill capitalize">{status.state}</span>
            </div>
          )}
        </header>
        <div className="flex h-[calc(100%-49px)]">
          <section className="relative flex-1 overflow-hidden">
            {!scanId && <StartPanel />}
            {scanId && view === "mindmap" && <Mindmap />}
            {scanId && view === "deps" && <DependencyGraph />}
            {scanId && view === "symbols" && <SymbolGraph />}
            {scanId && view === "cards" && <ModuleCards />}
            {scanId && view === "tech" && <TechRadar />}
            {scanId && view === "hotspots" && <Hotspots />}
            <ScanProgress />
          </section>
          {selected && <DetailPanel />}
        </div>
      </main>
    </div>
  );
}

function viewLabel(v: string): string {
  switch (v) {
    case "mindmap":
      return "Folder mindmap";
    case "deps":
      return "Dependency graph";
    case "symbols":
      return "Symbol graph";
    case "cards":
      return "Module cards";
    case "tech":
      return "Tech radar";
    case "hotspots":
      return "Hotspots";
    default:
      return v;
  }
}
