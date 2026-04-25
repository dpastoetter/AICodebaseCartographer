export function Placeholder({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="panel max-w-md p-8 text-center">
        <div className="mx-auto mb-4 h-px w-12 bg-slate-600" />
        <div className="text-sm font-semibold text-slate-200">{title}</div>
        {hint && <div className="mt-2 text-sm text-slate-500">{hint}</div>}
      </div>
    </div>
  );
}
