import { useEffect, useMemo, useRef } from "react";
import cytoscape, {
  type Core,
  type ElementDefinition,
  type NodeSingular,
} from "cytoscape";
import fcose from "cytoscape-fcose";

cytoscape.use(fcose);

interface Props {
  elements: ElementDefinition[];
  onSelect?: (id: string | null) => void;
  selected?: string | null;
  highlightColor?: string;
  edgeColor?: string;
  nodeColorByGroup?: boolean;
}

const GROUP_PALETTE = [
  "#7dd3fc",
  "#a78bfa",
  "#34d399",
  "#fbbf24",
  "#f472b6",
  "#fb7185",
  "#22d3ee",
  "#facc15",
];

export function CytoscapeView({
  elements,
  onSelect,
  selected,
  highlightColor = "#7dd3fc",
  edgeColor = "rgba(125, 211, 252, 0.35)",
  nodeColorByGroup = true,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  const groupColor = useMemo(() => {
    const groups = new Map<string, string>();
    return (g?: string) => {
      const key = g ?? "default";
      const existing = groups.get(key);
      if (existing) return existing;
      const color = GROUP_PALETTE[groups.size % GROUP_PALETTE.length];
      groups.set(key, color);
      return color;
    };
  }, [elements]);

  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      wheelSensitivity: 0.25,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele: NodeSingular) =>
              nodeColorByGroup
                ? groupColor(ele.data("group"))
                : highlightColor,
            "border-width": 1,
            "border-color": "rgba(255,255,255,0.1)",
            "label": "data(label)",
            "font-size": 9,
            "color": "#cbd5e1",
            "text-outline-color": "#0b0f1a",
            "text-outline-width": 2,
            "width": (ele: NodeSingular) => sizeFor(ele.data("size") ?? 1),
            "height": (ele: NodeSingular) => sizeFor(ele.data("size") ?? 1),
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-color": highlightColor,
            "border-width": 3,
          },
        },
        {
          selector: "edge",
          style: {
            "width": 1,
            "line-color": edgeColor,
            "target-arrow-color": edgeColor,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "opacity": 0.7,
          },
        },
        {
          selector: "edge.highlighted",
          style: {
            "line-color": highlightColor,
            "target-arrow-color": highlightColor,
            "width": 2,
            "opacity": 1,
          },
        },
        {
          selector: "node.dim",
          style: { opacity: 0.18 },
        },
        {
          selector: "edge.dim",
          style: { opacity: 0.05 },
        },
      ],
      layout: {
        name: "fcose",
        animate: false,
        randomize: true,
        nodeRepulsion: 4500,
        idealEdgeLength: 80,
        nodeSeparation: 60,
        gravity: 0.25,
      } as any,
    });

    cyRef.current = cy;

    cy.on("tap", "node", (e) => {
      const id = e.target.id();
      onSelect?.(id);
      highlight(cy, id);
    });
    cy.on("tap", (e) => {
      if (e.target === cy) {
        onSelect?.(null);
        clearHighlight(cy);
      }
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements, nodeColorByGroup, highlightColor, edgeColor]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (selected) {
      highlight(cy, selected);
    } else {
      clearHighlight(cy);
    }
  }, [selected]);

  return <div ref={containerRef} className="h-full w-full" />;
}

function sizeFor(value: number): number {
  const min = 14;
  const max = 60;
  const v = Math.max(0, Math.min(1, Math.log10(value + 1) / 3));
  return min + (max - min) * v;
}

function highlight(cy: Core, id: string) {
  const node = cy.getElementById(id);
  if (node.empty()) return;
  const neighborhood = node.closedNeighborhood();
  cy.elements().addClass("dim");
  neighborhood.removeClass("dim");
  cy.elements("edge").removeClass("highlighted");
  neighborhood.edges().addClass("highlighted");
}

function clearHighlight(cy: Core) {
  cy.elements().removeClass("dim");
  cy.elements("edge").removeClass("highlighted");
}
