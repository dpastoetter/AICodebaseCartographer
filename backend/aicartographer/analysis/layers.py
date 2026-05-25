"""Architecture map: cluster modules into layers from the dependency graph."""
from __future__ import annotations

from collections import Counter, defaultdict

from ..models import ArchitectureLayer, ArchitectureLayerEdge, ArchitectureMap, DependencyGraph
from ..scanner import load_artifact


def build_from_graph(deps: DependencyGraph, risks_count: dict[str, int] | None = None) -> ArchitectureMap:
    risks_count = risks_count or {}
    file_to_layer: dict[str, str] = {}
    for n in deps.nodes:
        file_to_layer[n.id] = n.group or "(root)"

    layer_files: dict[str, set[str]] = defaultdict(set)
    layer_lines: Counter[str] = Counter()
    for n in deps.nodes:
        layer = n.group or "(root)"
        layer_files[layer].add(n.id)
        layer_lines[layer] += n.lines

    edge_counts: Counter[tuple[str, str]] = Counter()
    for e in deps.edges:
        sl = file_to_layer.get(e.source, "(root)")
        tl = file_to_layer.get(e.target, "(root)")
        if sl != tl:
            edge_counts[(sl, tl)] += 1

    layers: list[ArchitectureLayer] = []
    for name in sorted(layer_files.keys(), key=lambda x: (-layer_lines[x], x)):
        layers.append(
            ArchitectureLayer(
                id=name,
                label=name,
                file_count=len(layer_files[name]),
                lines=layer_lines[name],
                risk_count=risks_count.get(name, 0),
            )
        )

    edges: list[ArchitectureLayerEdge] = []
    for (src, tgt), count in edge_counts.most_common(80):
        edges.append(ArchitectureLayerEdge(source=src, target=tgt, import_count=count))

    return ArchitectureMap(layers=layers, edges=edges)


def build_for_scan(scan_id: str) -> ArchitectureMap | None:
    data = load_artifact(scan_id, "dependencies.json")
    if not data:
        return None
    deps = DependencyGraph.model_validate(data)
    risks_count: dict[str, int] = Counter()
    risks = load_artifact(scan_id, "risks.json")
    if risks:
        for f in risks.get("findings") or []:
            path = f.get("path") if isinstance(f, dict) else None
            if not path:
                continue
            layer = path.split("/")[0] if "/" in path else "(root)"
            risks_count[layer] += 1
    return build_from_graph(deps, dict(risks_count))
