import { useStore } from "../store";

export function DetailPanel() {
  const selected = useStore((s) => s.selectedPath);
  const tree = useStore((s) => s.tree);
  const cards = useStore((s) => s.cards);
  const deps = useStore((s) => s.deps);
  const setSelected = useStore((s) => s.setSelected);

  if (!selected) return null;
  const node = findNode(tree?.root, selected);
  const card = cards[selected];

  const inboundDeps =
    deps?.edges.filter((e) => e.target === selected).map((e) => e.source) ?? [];
  const outboundDeps =
    deps?.edges.filter((e) => e.source === selected).map((e) => e.target) ?? [];

  return (
    <aside className="w-96 shrink-0 border-l border-white/5 bg-canvas-900/80 p-4 overflow-y-auto">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500">
            {node?.is_dir ? "Directory" : "File"}
          </div>
          <div className="font-semibold break-all">{node?.name ?? selected}</div>
          <div className="text-xs text-slate-400 break-all">{selected}</div>
        </div>
        <button onClick={() => setSelected(null)} className="text-slate-500 hover:text-white">
          ✕
        </button>
      </div>

      {node && (
        <div className="flex flex-wrap gap-1 mb-4">
          {node.language && <span className="pill">{node.language}</span>}
          <span className="pill">{node.lines} lines</span>
          <span className="pill">{(node.size / 1024).toFixed(1)} kB</span>
        </div>
      )}

      {card && (
        <section className="panel p-3 mb-4">
          <div className="text-xs uppercase tracking-widest text-slate-500 mb-1">
            AI summary
          </div>
          <div className="text-sm leading-relaxed">{card.summary}</div>
          {card.responsibilities.length > 0 && (
            <ul className="mt-3 list-disc list-inside text-xs text-slate-300 space-y-0.5">
              {card.responsibilities.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {(inboundDeps.length > 0 || outboundDeps.length > 0) && (
        <section className="panel p-3">
          <div className="text-xs uppercase tracking-widest text-slate-500 mb-2">
            Dependencies
          </div>
          {outboundDeps.length > 0 && (
            <div className="mb-2">
              <div className="text-xs font-medium text-slate-400 mb-1">
                Imports ({outboundDeps.length})
              </div>
              <ul className="text-xs space-y-0.5">
                {outboundDeps.slice(0, 25).map((p) => (
                  <li key={p}>
                    <button
                      className="text-accent hover:underline text-left break-all"
                      onClick={() => setSelected(p)}
                    >
                      {p}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {inboundDeps.length > 0 && (
            <div>
              <div className="text-xs font-medium text-slate-400 mb-1">
                Imported by ({inboundDeps.length})
              </div>
              <ul className="text-xs space-y-0.5">
                {inboundDeps.slice(0, 25).map((p) => (
                  <li key={p}>
                    <button
                      className="text-accent hover:underline text-left break-all"
                      onClick={() => setSelected(p)}
                    >
                      {p}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </aside>
  );
}

function findNode(
  root: { path: string; children: any[] } | undefined | null,
  path: string,
): any | null {
  if (!root) return null;
  if (root.path === path) return root;
  for (const c of root.children ?? []) {
    const r = findNode(c, path);
    if (r) return r;
  }
  return null;
}
