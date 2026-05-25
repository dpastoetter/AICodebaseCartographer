import { useEffect, useState } from "react";
import { api } from "../api";
import { IconClose } from "./Icons";

export function SecretsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [status, setStatus] = useState<Record<string, boolean> | null>(null);
  const [openai, setOpenai] = useState("");
  const [anthropic, setAnthropic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    api
      .secrets()
      .then((s) => setStatus(s))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [open]);

  if (!open) return null;

  async function save(provider: "openai" | "anthropic", key: string) {
    setError(null);
    setBusy(true);
    try {
      const s = await api.setSecret(provider, key);
      setStatus(s);
      if (provider === "openai") setOpenai("");
      if (provider === "anthropic") setAnthropic("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function clear(provider: "openai" | "anthropic") {
    setError(null);
    setBusy(true);
    try {
      const s = await api.clearSecret(provider);
      setStatus(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <div className="panel w-full max-w-xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <div>
            <div className="text-sm font-semibold text-slate-200">Configure API keys</div>
            <div className="mt-0.5 text-xs text-slate-500">
              Keys are stored encrypted locally on this machine.
            </div>
          </div>
          <button type="button" className="button !px-2" onClick={onClose}>
            <IconClose className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          <ProviderRow
            label="OpenAI"
            configured={!!status?.openai}
            placeholder="OPENAI_API_KEY"
            value={openai}
            setValue={setOpenai}
            onSave={() => save("openai", openai)}
            onClear={() => clear("openai")}
            busy={busy}
          />
          <ProviderRow
            label="Anthropic"
            configured={!!status?.anthropic}
            placeholder="ANTHROPIC_API_KEY"
            value={anthropic}
            setValue={setAnthropic}
            onSave={() => save("anthropic", anthropic)}
            onClear={() => clear("anthropic")}
            busy={busy}
          />
          {error && <div className="text-xs text-rose-300">{error}</div>}
        </div>
      </div>
    </div>
  );
}

function ProviderRow(props: {
  label: string;
  configured: boolean;
  placeholder: string;
  value: string;
  setValue: (v: string) => void;
  onSave: () => void;
  onClear: () => void;
  busy: boolean;
}) {
  return (
    <section className="rounded-lg border border-white/[0.06] bg-canvas-900/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {props.label}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            Status:{" "}
            <span className={props.configured ? "text-emerald-300/90" : "text-slate-400"}>
              {props.configured ? "configured" : "not configured"}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <button type="button" className="button" disabled={props.busy || !props.value.trim()} onClick={props.onSave}>
            Save
          </button>
          <button type="button" className="button !bg-white/[0.04]" disabled={props.busy || !props.configured} onClick={props.onClear}>
            Clear
          </button>
        </div>
      </div>
      <input
        className="input mt-3 font-mono text-xs"
        type="password"
        placeholder={props.placeholder}
        value={props.value}
        onChange={(e) => props.setValue(e.target.value)}
      />
    </section>
  );
}

