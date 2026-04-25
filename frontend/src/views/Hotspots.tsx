import { useStore } from "../store";
import type { HotspotEntry } from "../types";

export function Hotspots() {
  const hot = useStore((s) => s.hotspots);
  const setSelected = useStore((s) => s.setSelected);

  if (!hot) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500 text-sm">
        Computing hotspot metrics…
      </div>
    );
  }

  const sections: {
    title: string;
    metric: keyof HotspotEntry;
    suffix: string;
    list: HotspotEntry[];
  }[] = [
    {
      title: "Largest files",
      metric: "lines",
      suffix: "lines",
      list: hot.largest,
    },
    {
      title: "Most imported",
      metric: "fan_in",
      suffix: "imports",
      list: hot.most_imported,
    },
    {
      title: "Most complex",
      metric: "complexity",
      suffix: "score",
      list: hot.most_complex,
    },
    {
      title: "Recently changed (last year)",
      metric: "churn",
      suffix: "commits",
      list: hot.churn,
    },
  ];

  return (
    <div className="h-full overflow-y-auto p-6 grid gap-6 md:grid-cols-2">
      {sections.map((s) => (
        <section key={s.title} className="panel p-4">
          <h3 className="text-sm font-semibold text-slate-200 mb-3">{s.title}</h3>
          {s.list.length === 0 ? (
            <div className="text-xs text-slate-500">
              {s.metric === "churn" ? "No git history available." : "Nothing to show."}
            </div>
          ) : (
            <ul className="space-y-1.5">
              {s.list.map((entry) => (
                <li key={entry.path}>
                  <button
                    onClick={() => setSelected(entry.path)}
                    className="w-full flex items-center justify-between gap-3 text-left rounded-lg px-2 py-1.5 hover:bg-white/5 transition"
                  >
                    <div className="min-w-0">
                      <div className="text-sm truncate">
                        {entry.path.split("/").pop()}
                      </div>
                      <div className="text-[10px] text-slate-500 truncate">
                        {entry.path}
                      </div>
                    </div>
                    <Bar
                      value={Number(entry[s.metric] ?? 0)}
                      max={Math.max(
                        ...s.list.map((e) => Number(e[s.metric] ?? 0)),
                      )}
                      suffix={s.suffix}
                    />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </div>
  );
}

function Bar({
  value,
  max,
  suffix,
}: {
  value: number;
  max: number;
  suffix: string;
}) {
  const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="relative h-1.5 w-32 overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] text-slate-400 font-mono w-20 text-right">
        {value} {suffix}
      </span>
    </div>
  );
}
