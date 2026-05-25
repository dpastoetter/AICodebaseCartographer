import { useEffect, useMemo, useRef, useState } from "react";
import { buildSearchIndex, filterSearchResults, type SearchResult } from "../lib/searchIndex";
import { useStore } from "../store";

export function GlobalSearch() {
  const open = useStore((s) => s.searchOpen);
  const setOpen = useStore((s) => s.setSearchOpen);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const tree = useStore((s) => s.tree);
  const symbols = useStore((s) => s.symbols);
  const risks = useStore((s) => s.risks);
  const vulns = useStore((s) => s.vulns);
  const cards = useStore((s) => s.cards);
  const scanId = useStore((s) => s.scanId);
  const setView = useStore((s) => s.setView);
  const setSelected = useStore((s) => s.setSelected);

  const index = useMemo(
    () => buildSearchIndex({ tree, symbols, risks, vulns, cards }),
    [tree, symbols, risks, vulns, cards],
  );
  const results = useMemo(() => filterSearchResults(index, q), [index, q]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (scanId) setOpen(true);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [scanId]);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  useEffect(() => {
    setActive(0);
  }, [q]);

  if (!open || !scanId) return null;

  function pick(r: SearchResult) {
    setView(r.view);
    if (r.path) setSelected(r.path);
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, Math.max(0, results.length - 1)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[active]) {
      e.preventDefault();
      pick(results[active]);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] grid place-items-start bg-black/50 p-4 pt-[12vh]"
      onClick={() => setOpen(false)}
    >
      <div
        className="panel w-full max-w-xl overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          className="input w-full rounded-none border-0 border-b border-white/[0.06] bg-transparent px-4 py-3"
          placeholder="Search files, symbols, risks, vulnerabilities, summaries…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <ul className="max-h-80 overflow-y-auto py-1">
          {results.length === 0 ? (
            <li className="px-4 py-6 text-center text-sm text-slate-500">No matches.</li>
          ) : (
            results.map((r, i) => (
              <li key={r.id}>
                <button
                  type="button"
                  className={`flex w-full flex-col gap-0.5 px-4 py-2.5 text-left ${
                    i === active ? "bg-white/[0.06]" : "hover:bg-white/[0.03]"
                  }`}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => pick(r)}
                >
                  <div className="flex items-center gap-2">
                    <span className="pill text-[10px] uppercase">{r.kind}</span>
                    <span className="truncate text-sm font-medium text-slate-200">{r.label}</span>
                  </div>
                  <span className="truncate text-xs text-slate-500">{r.sublabel}</span>
                </button>
              </li>
            ))
          )}
        </ul>
        <div className="border-t border-white/[0.06] px-4 py-2 font-mono text-[10px] text-slate-600">
          ↑↓ navigate · Enter open · Esc close · Ctrl+K
        </div>
      </div>
    </div>
  );
}

export function GlobalSearchTrigger() {
  const scanId = useStore((s) => s.scanId);
  const setOpen = useStore((s) => s.setSearchOpen);

  if (!scanId) return null;

  return (
    <button
      type="button"
      className="button !bg-white/[0.04] font-mono text-xs"
      onClick={() => setOpen(true)}
      title="Search (Ctrl+K)"
    >
      Search
    </button>
  );
}
