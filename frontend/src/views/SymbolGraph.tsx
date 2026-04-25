import { useMemo, useState } from "react";
import type { ElementDefinition } from "cytoscape";
import { CytoscapeView } from "../components/CytoscapeView";
import { useStore } from "../store";
import type { FileNode } from "../types";

const KIND_COLORS: Record<string, string> = {
  class: "#818cf8",
  interface: "#5b9bd5",
  type: "#6b9b7a",
  function: "#64748b",
  method: "#b89a5c",
  variable: "#78716c",
};

export function SymbolGraph() {
  const symbols = useStore((s) => s.symbols);
  const tree = useStore((s) => s.tree);
  const setSelected = useStore((s) => s.setSelected);
  const [folder, setFolder] = useState<string>("");
  const [kind, setKind] = useState<string>("all");

  const folders = useMemo(() => collectTopFolders(tree?.root), [tree]);

  const filtered = useMemo(() => {
    if (!symbols) return null;
    return symbols.nodes.filter((n) => {
      if (folder && !n.file.startsWith(folder)) return false;
      if (kind !== "all" && n.kind !== kind) return false;
      return true;
    });
  }, [symbols, folder, kind]);

  const elements: ElementDefinition[] = useMemo(() => {
    if (!symbols || !filtered) return [];
    const ids = new Set(filtered.map((n) => n.id));
    const els: ElementDefinition[] = [];
    for (const n of filtered) {
      els.push({
        data: {
          id: n.id,
          label: n.parent ? `${n.parent}.${n.name}` : n.name,
          group: n.kind,
          size: 1,
          file: n.file,
          color: KIND_COLORS[n.kind] ?? "#64748b",
        },
      });
    }
    for (const e of symbols.edges) {
      if (ids.has(e.source) && ids.has(e.target)) {
        els.push({
          data: {
            id: `${e.source}->${e.target}`,
            source: e.source,
            target: e.target,
          },
        });
      }
    }
    return els;
  }, [filtered, symbols]);

  if (!symbols) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500 text-sm">
        Building symbol graph…
      </div>
    );
  }

  if (symbols.nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500 text-sm">
        No symbols extracted.
      </div>
    );
  }

  return (
    <div className="relative h-full">
      <div className="absolute left-4 top-3 z-10 flex flex-wrap items-center gap-2 rounded-md border border-white/[0.06] bg-canvas-900/90 px-3 py-1.5 font-mono text-[11px] text-slate-400 backdrop-blur-sm">
        <span>{filtered?.length ?? 0} symbols</span>
        <span className="text-slate-600">|</span>
        <select
          className="rounded border border-white/[0.1] bg-canvas-900 px-1.5 py-0.5 text-[11px] text-slate-300"
          value={folder}
          onChange={(e) => setFolder(e.target.value)}
        >
          <option value="">All folders</option>
          {folders.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <select
          className="rounded border border-white/[0.1] bg-canvas-900 px-1.5 py-0.5 text-[11px] text-slate-300"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          <option value="all">All symbol kinds</option>
          <option value="class">Classes</option>
          <option value="interface">Interfaces</option>
          <option value="function">Functions</option>
          <option value="method">Methods</option>
          <option value="type">Types</option>
        </select>
      </div>
      <CytoscapeView
        elements={elements}
        nodeColorByGroup
        onSelect={(id) => {
          if (!id) return setSelected(null);
          const node = symbols.nodes.find((n) => n.id === id);
          if (node) setSelected(node.file);
        }}
      />
    </div>
  );
}

function collectTopFolders(root: FileNode | undefined): string[] {
  if (!root) return [];
  const out: string[] = [];
  for (const c of root.children ?? []) {
    if (c.is_dir) out.push(c.path);
  }
  return out.sort();
}
