import { useMemo, useState } from "react";
import { IconDocument } from "../components/Icons";
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
      <div className="flex h-full items-center justify-center p-8 text-center">
        <div className="panel max-w-md p-8">
          <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-md border border-white/[0.08] bg-canvas-800 text-slate-400">
            <IconDocument className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-slate-100">Summaries disabled</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-500">
            This scan was run without an LLM. Re-run with{" "}
            <code className="rounded bg-canvas-700 px-1 py-0.5 font-mono text-xs text-accent">
              --llm anthropic
            </code>
            ,{" "}
            <code className="rounded bg-canvas-700 px-1 py-0.5 font-mono text-xs text-accent">
              --llm openai
            </code>
            , or{" "}
            <code className="rounded bg-canvas-700 px-1 py-0.5 font-mono text-xs text-accent">
              --llm ollama
            </code>{" "}
            to generate per-file summaries.
          </p>
        </div>
      </div>
    );
  }

  if (list.length === 0 && Object.keys(cards).length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        Waiting for summaries from {status?.llm.kind}…
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          className="input max-w-md min-w-48 flex-1"
          placeholder="Filter by path, summary, or responsibility…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <select className="input w-44" value={folder} onChange={(e) => setFolder(e.target.value)}>
          <option value="">All top-level folders</option>
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
      type="button"
      onClick={onOpen}
      className={`panel p-4 text-left transition hover:border-white/[0.12] ${
        isError ? "opacity-70" : ""
      }`}
    >
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <div className="truncate font-mono text-[11px] text-slate-500">{card.path}</div>
        {isError && <span className="pill border-rose-500/30 text-rose-300">error</span>}
      </div>
      <div className="mb-3 line-clamp-4 text-sm leading-relaxed text-slate-200">
        {card.summary || "(no summary)"}
      </div>
      {card.responsibilities.length > 0 && (
        <ul className="mb-3 list-inside list-disc space-y-0.5 text-xs text-slate-400">
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
