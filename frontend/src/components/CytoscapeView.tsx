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

/** Muted, distinguishable palette for categorical groups. */
const GROUP_PALETTE = [
  "#5b8bd9",
  "#7c8aa0",
  "#8b7ec8",
  "#b89a5c",
  "#5aada8",
  "#a67c8f",
  "#6b9b7a",
  "#9b8b6e",
];

export function CytoscapeView({
  elements,
  onSelect,
  selected,
  highlightColor = "#3b82f6",
  edgeColor = "rgba(59, 130, 246, 0.22)",
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
              nodeColorByGroup ? groupColor(ele.data("group")) : highlightColor,
            "border-width": 1,
            "border-color": "rgba(255,255,255,0.08)",
            label: "data(label)",
            "font-size": 9,
            color: "#cbd5e1",
            "text-outline-color": "#09090b",
            "text-outline-width": 2,
            width: (ele: NodeSingular) => sizeFor(ele.data("size") ?? 1),
            height: (ele: NodeSingular) => sizeFor(ele.data("size") ?? 1),
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-color": highlightColor,
            "border-width": 2,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": edgeColor,
            "target-arrow-color": edgeColor,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.65,
          },
        },
        {
          selector: "edge.highlighted",
          style: {
            "line-color": highlightColor,
            "target-arrow-color": highlightColor,
            width: 1.5,
            opacity: 1,
          },
        },
        {
          selector: "node.dim",
          style: { opacity: 0.14 },
        },
        {
          selector: "edge.dim",
          style: { opacity: 0.04 },
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
