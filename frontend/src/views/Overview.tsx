import { useStore } from "../store";

export function Overview() {
  const brief = useStore((s) => s.brief);
  const status = useStore((s) => s.status);

  if (!brief) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        Building architecture brief…
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <section className="panel mb-4 p-6">
        <div className="label-upper mb-2">Architecture brief</div>
        <h2 className="text-xl font-semibold text-slate-100">{brief.project_name}</h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-300">{brief.purpose}</p>
        {status && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            <span className="pill">{status.totals.files} files</span>
            <span className="pill">{status.totals.lines} lines</span>
            <span className="pill">{status.totals.languages} languages</span>
          </div>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <InfoCard title="Modules" body={brief.modules} />
        <InfoCard title="Technology" body={brief.tech_stack} />
        <InfoCard title="Dependency hubs" body={brief.dependency_hubs} />
        {brief.hotspots_note && <InfoCard title="Hotspots" body={brief.hotspots_note} />}
      </div>

      {(brief.top_risks.length > 0 || brief.top_vulns.length > 0) && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {brief.top_risks.length > 0 && (
            <section className="panel p-4">
              <div className="label-upper mb-2">Top risks</div>
              <ul className="space-y-2 text-sm text-slate-400">
                {brief.top_risks.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </section>
          )}
          {brief.top_vulns.length > 0 && (
            <section className="panel p-4">
              <div className="label-upper mb-2">Top vulnerabilities</div>
              <ul className="space-y-2 text-sm text-slate-400">
                {brief.top_vulns.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

function InfoCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="panel p-4">
      <div className="label-upper mb-2">{title}</div>
      <p className="text-sm text-slate-400">{body}</p>
    </section>
  );
}
