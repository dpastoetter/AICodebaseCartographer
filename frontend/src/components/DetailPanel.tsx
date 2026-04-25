import { useStore } from "../store";
import type { FileNode } from "../types";
import { IconClose } from "./Icons";

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
    <aside className="w-[22rem] shrink-0 overflow-y-auto border-l border-white/[0.06] bg-canvas-900/95 p-4">
      <div className="mb-4 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="label-upper">{node?.is_dir ? "Directory" : "File"}</div>
          <div className="mt-1 font-semibold text-slate-100">{node?.name ?? selected}</div>
          <div className="mt-0.5 break-all font-mono text-[11px] text-slate-500">{selected}</div>
        </div>
        <button
          type="button"
          onClick={() => setSelected(null)}
          className="rounded-md p-1.5 text-slate-500 transition hover:bg-white/[0.06] hover:text-slate-200"
          aria-label="Close panel"
        >
          <IconClose className="h-5 w-5" />
        </button>
      </div>

      {node && (
        <div className="mb-4 flex flex-wrap gap-1">
          {node.language && <span className="pill">{node.language}</span>}
          <span className="pill">{node.lines} lines</span>
          <span className="pill">{(node.size / 1024).toFixed(1)} kB</span>
        </div>
      )}

      {card && (
        <section className="panel mb-4 p-3">
          <div className="label-upper mb-2">Summary</div>
          <div className="text-sm leading-relaxed text-slate-300">{card.summary}</div>
          {card.responsibilities.length > 0 && (
            <ul className="mt-3 list-inside list-disc space-y-1 text-xs text-slate-400">
              {card.responsibilities.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {(inboundDeps.length > 0 || outboundDeps.length > 0) && (
        <section className="panel p-3">
          <div className="label-upper mb-2">Dependencies</div>
          {outboundDeps.length > 0 && (
            <div className="mb-3">
              <div className="mb-1 text-xs font-medium text-slate-500">Imports ({outboundDeps.length})</div>
              <ul className="space-y-0.5 text-xs">
                {outboundDeps.slice(0, 25).map((p) => (
                  <li key={p}>
                    <button
                      type="button"
                      className="break-all text-left text-accent hover:underline"
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
              <div className="mb-1 text-xs font-medium text-slate-500">Imported by ({inboundDeps.length})</div>
              <ul className="space-y-0.5 text-xs">
                {inboundDeps.slice(0, 25).map((p) => (
                  <li key={p}>
                    <button
                      type="button"
                      className="break-all text-left text-accent hover:underline"
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

function findNode(root: FileNode | undefined | null, path: string): FileNode | null {
  if (!root) return null;
  if (root.path === path) return root;
  for (const c of root.children ?? []) {
    const r = findNode(c, path);
    if (r) return r;
  }
  return null;
}
