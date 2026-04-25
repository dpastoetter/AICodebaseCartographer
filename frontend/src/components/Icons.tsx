/** Inline SVG icons — no emoji, consistent stroke weight for a product UI. */
import type { ReactNode } from "react";

const stroke = {
  fill: "none" as const,
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

function Svg({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden
    >
      {children}
    </svg>
  );
}

export function LogoMark({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <path {...stroke} d="M5 7h14M5 12h10M5 17h12" />
    </Svg>
  );
}

export function IconMindmap({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <path {...stroke} d="M12 3v18M8 8h8M8 13h5M8 18h8" />
    </Svg>
  );
}

export function IconDependencies({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <circle {...stroke} cx="6" cy="6" r="2.5" />
      <circle {...stroke} cx="18" cy="6" r="2.5" />
      <circle {...stroke} cx="12" cy="18" r="2.5" />
      <path {...stroke} d="M7.8 7.8l2.8 8.4M16.2 7.8l-2.8 8.4" />
    </Svg>
  );
}

export function IconSymbols({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <path {...stroke} d="M9 4L5 8l4 4M15 4l4 4-4 4M9 20h6" />
    </Svg>
  );
}

export function IconModuleCards({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <rect {...stroke} x="4" y="4" width="16" height="10" rx="1.5" />
      <path {...stroke} d="M4 14h16M8 18h8" />
    </Svg>
  );
}

export function IconTechRadar({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <path {...stroke} d="M12 12V4M12 12l6.5 3.75M12 12l-6.5 3.75" />
      <circle {...stroke} cx="12" cy="12" r="9" opacity={0.35} />
    </Svg>
  );
}

export function IconHotspots({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <path {...stroke} d="M4 19V5M10 19V9M16 19v-6M22 19V8" />
    </Svg>
  );
}

export function IconRisks({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <path {...stroke} d="M12 3l9 16H3l9-16Z" />
      <path {...stroke} d="M12 9v5" />
      <path {...stroke} d="M12 17h.01" />
    </Svg>
  );
}

export function IconDocument({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <path {...stroke} d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path {...stroke} d="M14 2v6h6M9 13h6M9 17h4" />
    </Svg>
  );
}

export function IconClose({ className }: { className?: string }) {
  return (
    <Svg className={className}>
      <path {...stroke} d="M18 6L6 18M6 6l12 12" />
    </Svg>
  );
}
