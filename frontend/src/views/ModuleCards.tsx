import { useMemo, useState } from "react";
import { useStore } from "../store";
import type { ModuleCard } from "../types";

export function ModuleCards() {
  const cards = useStore((s) => s.cards);
  const status = useStore((s) => s.status);
  const setSelected = useStore((s) => s.setSelected);
  const [filter, setFilter] = useState("");
  const [folder, setFolder] = useState("");

  const list = useMemo(() => {
    let items = Object.values(cards);
    if (folder) items = items.filter((c) => c.path.startsWith(folder));
    if (filter) {
      const f = filter.toLowerCase();
      items = items.filter(
        (c) =>
          c.path.toLowerCase().includes(f) ||
          c.summary.toLowerCase().includes(f) ||
          c.responsibilities.some((r) => r.toLowerCase().includes(f)),
      );
    }
    items.sort((a, b) => a.path.localeCompare(b.path));
    return items;
  }, [cards, filter, folder]);

  const folders = useMemo(() => {
    const set = new Set<string>();
    for (const c of Object.values(cards)) {
      const top = c.path.split("/")[0];
      if (top) set.add(top);
    }
    return Array.from(set).sort();
  }, [cards]);

  const isLLM = status?.llm.kind && status.llm.kind !== "none";

  if (!isLLM) {
    return (
      <div className="flex h-full items-center justify-center text-center p-8">
        <div className="panel p-6 max-w-md">
          <div className="text-3xl mb-2">📇</div>
          <h3 className="font-semibold">No LLM provider configured</h3>
          <p className="mt-2 text-sm text-slate-400">
            Re-run the scan with{" "}
            <code className="text-accent">--llm anthropic</code>,{" "}
            <code className="text-accent">--llm openai</code> or{" "}
            <code className="text-accent">--llm ollama</code> to generate
            natural-language summaries for every module.
          </p>
        </div>
      </div>
    );
  }

  if (list.length === 0 && Object.keys(cards).length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500 text-sm">
        Waiting for first card from {status?.llm.kind}…
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          className="input flex-1 min-w-48 max-w-md"
          placeholder="Search summaries, paths, responsibilities…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <select
          className="input w-44"
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
        <span className="pill">
          {Object.keys(cards).length} cards
          {status && status.progress.cards_total > 0 && (
            <>
              {" "}
              · {status.progress.cards_done}/{status.progress.cards_total}
            </>
          )}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {list.map((card) => (
          <Card key={card.path} card={card} onOpen={() => setSelected(card.path)} />
        ))}
      </div>
    </div>
  );
}

function Card({ card, onOpen }: { card: ModuleCard; onOpen: () => void }) {
  const isError = card.status === "error";
  return (
    <button
      onClick={onOpen}
      className={`panel p-4 text-left hover:border-accent/30 transition ${
        isError ? "opacity-70" : ""
      }`}
    >
      <div className="flex items-baseline justify-between gap-2 mb-1">
        <div className="font-mono text-xs text-slate-400 truncate">
          {card.path}
        </div>
        {isError && <span className="pill text-rose-300">error</span>}
      </div>
      <div className="text-sm leading-relaxed text-slate-100 mb-3 line-clamp-4">
        {card.summary || "(no summary)"}
      </div>
      {card.responsibilities.length > 0 && (
        <ul className="list-disc list-inside text-xs text-slate-300 space-y-0.5 mb-3">
          {card.responsibilities.slice(0, 3).map((r, i) => (
            <li key={i} className="line-clamp-1">
              {r}
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap gap-1">
        {card.tech.slice(0, 6).map((t) => (
          <span key={t} className="pill">
            {t}
          </span>
        ))}
      </div>
    </button>
  );
}
