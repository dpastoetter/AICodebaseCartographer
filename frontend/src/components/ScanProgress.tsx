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
    <div className="absolute bottom-4 right-4 z-30 panel p-4 w-80">
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-block h-2 w-2 rounded-full bg-accent animate-pulse" />
        <span className="text-sm font-semibold capitalize">{status.state}</span>
      </div>
      <div className="text-xs text-slate-400 mb-3">{p.message}</div>
      <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full bg-accent transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
        <span>
          {p.files_parsed}/{p.files_seen} files
        </span>
        {p.cards_total > 0 && (
          <span>
            {p.cards_done}/{p.cards_total} cards
          </span>
        )}
      </div>
    </div>
  );
}
