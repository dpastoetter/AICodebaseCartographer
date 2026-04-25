import { useStore } from "../store";

export function ScanProgress() {
  const status = useStore((s) => s.status);
  if (!status) return null;
  const showOverlay = status.state !== "done" && status.state !== "error";
  if (!showOverlay) return null;

  const p = status.progress;
  const pct =
    p.files_seen > 0
      ? Math.min(100, Math.round((p.files_parsed / Math.max(1, p.files_seen)) * 100))
      : 0;

  return (
    <div className="absolute bottom-4 right-4 z-30 w-80 rounded-lg border border-white/[0.08] bg-canvas-900/95 p-4 shadow-panel backdrop-blur-sm">
      <div className="mb-2 flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/40 opacity-60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
        </span>
        <span className="font-mono text-xs font-medium uppercase tracking-wide text-slate-300">
          {status.state}
        </span>
      </div>
      <p className="mb-3 text-xs text-slate-500">{p.message}</p>
      <div className="h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className="h-full rounded-full bg-accent transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-slate-500">
        <span>
          {p.files_parsed}/{p.files_seen} files
        </span>
        {p.cards_total > 0 && (
          <span>
            {p.cards_done}/{p.cards_total} summaries
          </span>
        )}
      </div>
    </div>
  );
}
