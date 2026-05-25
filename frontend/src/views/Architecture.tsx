import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
import type { ArchitectureMap } from "../types";

export function Architecture() {
  const scanId = useStore((s) => s.scanId);
  const setView = useStore((s) => s.setView);
  const [map, setMap] = useState<ArchitectureMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [layerFilter, setLayerFilter] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;
    api
      .architecture(scanId)
      .then(setMap)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [scanId]);

  const maxLines = useMemo(
    () => Math.max(1, ...(map?.layers.map((l) => l.lines) ?? [1])),
    [map],
  );

  if (error) {
    return (
      <div className="p-6 text-sm text-rose-300">{error}</div>
    );
  }

  if (!map) {
    return <div className="p-6 text-sm text-slate-500">Loading architecture map…</div>;
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <p className="text-xs text-slate-500">
        Folder layers from the dependency graph. Cross-layer edges are aggregated imports. Click a layer
        to filter Dependencies.
      </p>

      <div className="mt-6 space-y-3">
        {map.layers.map((layer) => {
          const w = Math.round((layer.lines / maxLines) * 100);
          const active = layerFilter === layer.id;
          return (
            <button
              key={layer.id}
              type="button"
              className={`panel w-full p-4 text-left transition ${active ? "ring-1 ring-accent/50" : ""}`}
              onClick={() => {
                const next = active ? null : layer.id;
                setLayerFilter(next);
                if (next) setView("deps");
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-sm font-medium text-slate-100">{layer.label}</span>
                <span className="text-xs text-slate-500">
                  {layer.file_count} files · {layer.lines.toLocaleString()} lines
                  {layer.risk_count > 0 && (
                    <span className="ml-2 text-amber-300">{layer.risk_count} risks</span>
                  )}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded bg-white/[0.04]">
                <div
                  className="h-full rounded bg-accent/60"
                  style={{ width: `${w}%` }}
                />
              </div>
            </button>
          );
        })}
      </div>

      {map.edges.length > 0 && (
        <section className="panel mt-6 p-4">
          <div className="text-sm font-semibold text-slate-200">Cross-layer imports</div>
          <ul className="mt-3 max-h-64 space-y-1 overflow-y-auto font-mono text-xs text-slate-400">
            {map.edges.slice(0, 40).map((e, i) => (
              <li key={i}>
                <span className="text-slate-300">{e.source}</span>
                <span className="text-slate-600"> → </span>
                <span className="text-slate-300">{e.target}</span>
                <span className="text-slate-600"> ({e.import_count})</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
