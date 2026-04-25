import { useEffect, useMemo, useRef } from "react";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";
import { useStore } from "../store";
import type { FileNode } from "../types";

const transformer = new Transformer();

function nodeToMarkdown(node: FileNode, depth: number): string {
  const heading = "#".repeat(Math.min(depth + 1, 6));
  const lines: string[] = [];

  const label = node.is_dir
    ? node.name || "/"
    : `${node.name}${node.lines ? ` · ${node.lines} lines` : ""}${langTag(node.language)}`;
  lines.push(`${heading} ${label}`);

  for (const child of node.children) {
    lines.push(nodeToMarkdown(child, depth + 1));
  }
  return lines.join("\n");
}

function langTag(lang: string | null): string {
  if (!lang) return "";
  const map: Record<string, string> = {
    python: " · py",
    javascript: " · js",
    typescript: " · ts",
    tsx: " · tsx",
    rust: " · rs",
    go: " · go",
    markdown: " · md",
    json: " · json",
    toml: " · toml",
    yaml: " · yaml",
    css: " · css",
    scss: " · scss",
    html: " · html",
  };
  return map[lang] ?? ` · ${lang}`;
}

export function Mindmap() {
  const tree = useStore((s) => s.tree);
  const setSelected = useStore((s) => s.setSelected);
  const ref = useRef<SVGSVGElement | null>(null);
  const mmRef = useRef<Markmap | null>(null);

  const markdown = useMemo(() => {
    if (!tree) return "";
    return nodeToMarkdown(tree.root, 0);
  }, [tree]);

  useEffect(() => {
    if (!markdown || !ref.current) return;
    const { root } = transformer.transform(markdown);

    if (!mmRef.current) {
      mmRef.current = Markmap.create(
        ref.current,
        {
          duration: 250,
          maxWidth: 280,
          spacingHorizontal: 80,
          spacingVertical: 8,
          paddingX: 16,
          color: () => "#64748b",
        },
        root,
      );
    } else {
      mmRef.current.setData(root);
      mmRef.current.fit();
    }
  }, [markdown]);

  useEffect(() => {
    return () => {
      mmRef.current?.destroy();
      mmRef.current = null;
    };
  }, []);

  if (!tree) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        Loading tree…
      </div>
    );
  }

  return (
    <div className="relative h-full">
      <svg
        ref={ref}
        className="h-full w-full"
        onClick={(e) => {
          const target = e.target as Element;
          const text = target.closest("g.markmap-node")?.textContent;
          if (!text) return;
          const path = pathFromLabel(tree.root, text.trim());
          if (path) setSelected(path);
        }}
      />
    </div>
  );
}

function pathFromLabel(root: FileNode, label: string): string | null {
  const stripped = label.replace(/^[^\w]*/, "").trim();
  if (!stripped) return null;
  function walk(node: FileNode): string | null {
    if (node.name && (node.name === stripped || stripped.startsWith(node.name))) {
      return node.path;
    }
    for (const c of node.children) {
      const r = walk(c);
      if (r) return r;
    }
    return null;
  }
  return walk(root);
}
