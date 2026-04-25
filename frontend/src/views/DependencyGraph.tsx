import { useMemo } from "react";
import type { ElementDefinition } from "cytoscape";
import { CytoscapeView } from "../components/CytoscapeView";
import { useStore } from "../store";

export function DependencyGraph() {
  const deps = useStore((s) => s.deps);
  const selected = useStore((s) => s.selectedPath);
  const setSelected = useStore((s) => s.setSelected);

  const elements: ElementDefinition[] = useMemo(() => {
    if (!deps) return [];
    const els: ElementDefinition[] = [];
    for (const n of deps.nodes) {
      els.push({
        data: {
          id: n.id,
          label: n.label,
          group: n.group ?? "(root)",
          size: n.lines || 1,
          language: n.language,
        },
      });
    }
    for (const e of deps.edges) {
      els.push({
        data: {
          id: `${e.source}->${e.target}`,
          source: e.source,
          target: e.target,
          kind: e.kind,
        },
      });
    }
    return els;
  }, [deps]);

  if (!deps) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500 text-sm">
        Building dependency graph…
      </div>
    );
  }

  if (deps.nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500 text-sm">
        No imports were detected.
      </div>
    );
  }

  return (
    <div className="relative h-full">
      <div className="absolute top-3 left-4 z-10 panel px-3 py-1.5 text-xs flex items-center gap-3">
        <span>{deps.nodes.length} files</span>
        <span className="text-slate-500">·</span>
        <span>{deps.edges.length} imports</span>
        <span className="text-slate-500">·</span>
        <span className="text-slate-500">click a node to focus its neighborhood</span>
      </div>
      <CytoscapeView
        elements={elements}
        selected={selected}
        onSelect={(id) => setSelected(id)}
      />
    </div>
  );
}
