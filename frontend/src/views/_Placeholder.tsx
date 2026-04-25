export function Placeholder({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="panel max-w-md p-8 text-center">
        <div className="text-3xl mb-2">…</div>
        <div className="text-lg font-semibold">{title}</div>
        {hint && <div className="mt-2 text-sm text-slate-400">{hint}</div>}
      </div>
    </div>
  );
}
