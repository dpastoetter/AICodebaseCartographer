import { create } from "zustand";
import type {
  DependencyGraph,
  Hotspots,
  ModuleCard,
  RisksReport,
  ScanStatus,
  SymbolGraph,
  TechRadar,
  TreeResponse,
} from "./types";
import { api, subscribeToScan } from "./api";

export type ViewKey =
  | "mindmap"
  | "deps"
  | "symbols"
  | "cards"
  | "tech"
  | "hotspots"
  | "risks";

interface State {
  scanId: string | null;
  status: ScanStatus | null;
  view: ViewKey;
  tree: TreeResponse | null;
  deps: DependencyGraph | null;
  symbols: SymbolGraph | null;
  tech: TechRadar | null;
  hotspots: Hotspots | null;
  risks: RisksReport | null;
  cards: Record<string, ModuleCard>;
  selectedPath: string | null;
  unsubscribe: (() => void) | null;
  setView: (view: ViewKey) => void;
  setSelected: (path: string | null) => void;
  attachToScan: (scanId: string) => Promise<void>;
  startRepoScan: (repo: string, apiKey?: string | null) => Promise<void>;
  reloadArtifacts: () => Promise<void>;
}

export const useStore = create<State>((set, get) => ({
  scanId: null,
  status: null,
  view: "mindmap",
  tree: null,
  deps: null,
  symbols: null,
  tech: null,
  hotspots: null,
  risks: null,
  cards: {},
  selectedPath: null,
  unsubscribe: null,

  setView: (view) => set({ view }),
  setSelected: (selectedPath) => set({ selectedPath }),

  attachToScan: async (scanId: string) => {
    const prev = get().unsubscribe;
    if (prev) prev();
    set({
      scanId,
      status: null,
      tree: null,
      deps: null,
      symbols: null,
      tech: null,
      hotspots: null,
      risks: null,
      cards: {},
      selectedPath: null,
    });

    try {
      const status = await api.getScan(scanId);
      set({ status });
    } catch (e) {
      console.error("attachToScan", e);
    }

    const unsub = subscribeToScan(scanId, async (event) => {
      if (event.type === "status") {
        set({ status: event.status });
        const isDone = event.status.state === "done" || event.status.state === "error";
        if (isDone) {
          await get().reloadArtifacts();
        }
        if (
          event.status.state === "analyzing" ||
          event.status.state === "summarizing"
        ) {
          await get().reloadArtifacts();
        }
      } else if (event.type === "progress") {
        const status = get().status;
        if (status) set({ status: { ...status, progress: event.progress } });
      } else if (event.type === "card") {
        set((s) => ({ cards: { ...s.cards, [event.card.path]: event.card } }));
      }
    });
    set({ unsubscribe: unsub });

    if (get().status?.state === "done") {
      await get().reloadArtifacts();
    }
  },

  startRepoScan: async (repo: string, apiKey?: string | null) => {
    const status = await api.startScanFromRepo({ repo, llm: "none", api_key: apiKey ?? null });
    const url = new URL(window.location.href);
    url.searchParams.set("scan", status.scan_id);
    window.history.replaceState({}, "", url);
    await get().attachToScan(status.scan_id);
  },

  reloadArtifacts: async () => {
    const id = get().scanId;
    if (!id) return;
    const safe = async <T>(p: Promise<T>): Promise<T | null> => {
      try {
        return await p;
      } catch {
        return null;
      }
    };
    const [tree, deps, symbols, tech, hotspots, risks, cards] = await Promise.all([
      safe(api.tree(id)),
      safe(api.deps(id)),
      safe(api.symbols(id)),
      safe(api.tech(id)),
      safe(api.hotspots(id)),
      safe(api.risks(id)),
      safe(api.cards(id)),
    ]);
    set((s) => {
      const next: Partial<State> = {};
      if (tree) next.tree = tree;
      if (deps) next.deps = deps;
      if (symbols) next.symbols = symbols;
      if (tech) next.tech = tech;
      if (hotspots) next.hotspots = hotspots;
      if (risks) next.risks = risks;
      if (cards) {
        const map = { ...s.cards };
        for (const c of cards.cards) map[c.path] = c;
        next.cards = map;
      }
      return next;
    });
  },
}));
