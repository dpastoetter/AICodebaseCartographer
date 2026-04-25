import { useStore } from "../store";
import type { TechItem } from "../types";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const LANG_COLORS: Record<string, string> = {
  python: "#4d7ccf",
  javascript: "#c4a35a",
  typescript: "#5b9bd5",
  tsx: "#5b8bd9",
  rust: "#b87a5c",
  go: "#5aada8",
  java: "#8b7ec8",
  c: "#7c8aa0",
  cpp: "#7c8aa0",
  ruby: "#a67c8f",
  markdown: "#64748b",
  json: "#9b8b6e",
  yaml: "#6b9b7a",
  toml: "#6b9b7a",
  html: "#8b7ec8",
  css: "#6b9b7a",
  scss: "#6b9b7a",
};

export function TechRadar() {
  const tech = useStore((s) => s.tech);

  if (!tech) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500 text-sm">
        Loading technology profile…
      </div>
    );
  }

  const langData = tech.languages.map((l) => ({
    name: l.name,
    lines: l.lines,
    files: l.files,
    fill: LANG_COLORS[l.name] ?? "#5b8bd9",
  }));

  const groups = groupItems(tech.items);

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="panel p-4 lg:col-span-2">
          <h3 className="mb-3 text-sm font-semibold text-slate-200">Languages by lines of code</h3>
          {langData.length === 0 ? (
            <div className="text-xs text-slate-500">No language data.</div>
          ) : (
            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <BarChart data={langData} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid stroke="#1f2229" strokeDasharray="3 3" />
                  <XAxis type="number" stroke="#64748b" fontSize={11} />
                  <YAxis
                    dataKey="name"
                    type="category"
                    stroke="#cbd5e1"
                    fontSize={12}
                    width={100}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0f1014",
                      border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 6,
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="lines">
                    {langData.map((d) => (
                      <Cell key={d.name} fill={d.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            {tech.languages.map((l) => (
              <div
                key={l.name}
                className="rounded-lg border border-white/5 bg-white/5 p-2"
              >
                <div className="font-medium">{l.name}</div>
                <div className="text-slate-400">
                  {l.files} files · {l.lines} lines
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-200">Manifest sources</h3>
          <ul className="text-xs space-y-1">
            {Array.from(new Set(tech.items.map((i) => i.source))).map((src) => (
              <li key={src} className="text-slate-300 truncate">
                {src}
              </li>
            ))}
            {tech.items.length === 0 && (
              <li className="text-slate-500">No manifests detected.</li>
            )}
          </ul>
        </section>
      </div>

      <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {Object.entries(groups).map(([category, items]) => (
          <section key={category} className="panel p-4">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">
              {category}{" "}
              <span className="text-xs font-normal text-slate-500">
                ({items.length})
              </span>
            </h3>
            <ul className="space-y-1.5">
              {items.map((it, i) => (
                <li
                  key={`${it.name}-${i}`}
                  className="flex items-baseline justify-between gap-2 text-sm"
                >
                  <span className="font-medium truncate">{it.name}</span>
                  {it.version && (
                    <span className="text-[11px] text-slate-500 font-mono shrink-0">
                      {it.version}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

function groupItems(items: TechItem[]): Record<string, TechItem[]> {
  const groups: Record<string, TechItem[]> = {};
  for (const it of items) {
    const key = it.category ?? labelForKind(it.kind);
    (groups[key] ??= []).push(it);
  }
  for (const arr of Object.values(groups)) {
    arr.sort((a, b) => a.name.localeCompare(b.name));
  }
  return groups;
}

function labelForKind(kind: TechItem["kind"]): string {
  switch (kind) {
    case "framework":
      return "Frameworks";
    case "library":
      return "Libraries";
    case "language":
      return "Languages";
    case "runtime":
      return "Runtimes";
    case "tool":
      return "Tooling";
  }
}
