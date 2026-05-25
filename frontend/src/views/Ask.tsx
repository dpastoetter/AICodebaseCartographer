import { useCallback, useRef, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
import type { AskCitation, AskResponse, LLMKind } from "../types";

export function Ask() {
  const scanId = useStore((s) => s.scanId);
  const setView = useStore((s) => s.setView);
  const setSelected = useStore((s) => s.setSelected);

  const [question, setQuestion] = useState("");
  const [llm, setLlm] = useState<LLMKind>("openai");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<{ q: string; a: AskResponse }[]>([]);
  const streamRef = useRef<EventSource | null>(null);

  const submit = useCallback(async () => {
    if (!scanId || !question.trim()) return;
    setBusy(true);
    setError(null);
    setAnswer(null);
    streamRef.current?.close();

    try {
      const result = await new Promise<AskResponse>((resolve, reject) => {
        const es = api.askStream(scanId, { question: question.trim(), llm });
        streamRef.current = es;
        es.addEventListener("answer", (msg: MessageEvent) => {
          try {
            resolve(JSON.parse(msg.data) as AskResponse);
          } catch (e) {
            reject(e);
          }
          es.close();
        });
        es.onerror = () => {
          es.close();
          reject(new Error("Ask stream failed"));
        };
      });
      setAnswer(result);
      setHistory((h) => [...h, { q: question.trim(), a: result }]);
      setQuestion("");
    } catch {
      try {
        const result = await api.ask(scanId, { question: question.trim(), llm });
        setAnswer(result);
        setHistory((h) => [...h, { q: question.trim(), a: result }]);
        setQuestion("");
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setBusy(false);
    }
  }, [scanId, question, llm]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        <p className="text-xs text-slate-500">
          Grounded Q&amp;A over this scan&apos;s artifacts. Answers cite paths, risks, and graph edges from
          the analysis — not a generic chat model.
        </p>

        {history.length > 0 && (
          <div className="mt-4 space-y-4">
            {history.map((item, i) => (
              <div key={i} className="space-y-2">
                <div className="panel border-accent/20 p-3 text-sm text-slate-200">{item.q}</div>
                <AnswerBlock
                  response={item.a}
                  onCitation={(c) => openCitation(c, setView, setSelected)}
                />
              </div>
            ))}
          </div>
        )}

        {answer && history.length === 0 && (
          <div className="mt-4">
            <AnswerBlock response={answer} onCitation={(c) => openCitation(c, setView, setSelected)} />
          </div>
        )}

        {!answer && history.length === 0 && !busy && (
          <div className="panel mt-4 p-6 text-sm text-slate-500">
            Example: &quot;Where is authentication handled?&quot; or &quot;What depends on the scanner
            module?&quot;
          </div>
        )}
      </div>

      <footer className="border-t border-white/[0.06] bg-canvas-900/80 p-4">
        {error && <p className="mb-2 text-xs text-rose-300">{error}</p>}
        <div className="flex flex-wrap items-end gap-2">
          <select
            className="input w-28 font-mono text-xs"
            value={llm}
            onChange={(e) => setLlm(e.target.value as LLMKind)}
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="none">No LLM</option>
          </select>
          <input
            className="input min-w-0 flex-1 font-mono text-xs"
            placeholder="Ask about this codebase…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void submit();
              }
            }}
            disabled={busy}
          />
          <button type="button" className="button" disabled={busy || !question.trim()} onClick={() => void submit()}>
            {busy ? "Thinking…" : "Ask"}
          </button>
        </div>
      </footer>
    </div>
  );
}

function AnswerBlock({
  response,
  onCitation,
}: {
  response: AskResponse;
  onCitation: (c: AskCitation) => void;
}) {
  return (
    <div className="panel p-4">
      <div className="prose prose-invert max-w-none whitespace-pre-wrap text-sm text-slate-200">
        {response.answer}
      </div>
      {response.citations.length > 0 && (
        <div className="mt-4 border-t border-white/[0.06] pt-3">
          <div className="label-upper mb-2">Citations</div>
          <ul className="flex flex-wrap gap-2">
            {response.citations.map((c, i) => (
              <li key={i}>
                <button
                  type="button"
                  className="pill cursor-pointer hover:border-accent/40"
                  onClick={() => onCitation(c)}
                >
                  {c.label}
                  {c.line != null ? `:${c.line}` : ""}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function openCitation(
  c: AskCitation,
  setView: (v: import("../store").ViewKey) => void,
  setSelected: (p: string | null) => void,
) {
  if (c.path) setSelected(c.path);
  const k = c.kind;
  if (k === "risk" || k === "vuln") setView("risks");
  else if (k === "symbol") setView("symbols");
  else if (k === "file") setView("mindmap");
}
