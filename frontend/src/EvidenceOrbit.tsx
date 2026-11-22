import type { Comparison } from "./types";

export default function EvidenceOrbit({
  comparison,
}: {
  comparison: Comparison | null;
}) {
  return (
    <div className="evidence-orbit">
      <svg viewBox="0 0 400 320" aria-hidden="true">
        <defs>
          <radialGradient id="lab-core">
            <stop stopColor="#67e8f9" />
            <stop offset="1" stopColor="#8b5cf6" />
          </radialGradient>
        </defs>
        <g className="orbit-track">
          <ellipse cx="200" cy="160" rx="160" ry="62" />
          <ellipse
            cx="200"
            cy="160"
            rx="160"
            ry="62"
            transform="rotate(60 200 160)"
          />
          <ellipse
            cx="200"
            cy="160"
            rx="160"
            ry="62"
            transform="rotate(120 200 160)"
          />
        </g>
        <g className="orbit-satellites">
          <circle cx="40" cy="160" r="6" />
          <circle cx="280" cy="298" r="5" />
          <circle cx="280" cy="22" r="5" />
        </g>
        <circle cx="200" cy="160" r="53" fill="url(#lab-core)" opacity=".12" />
        <circle cx="200" cy="160" r="43" fill="none" stroke="url(#lab-core)" />
        <text
          x="200"
          y="178"
          textAnchor="middle"
          fill="currentColor"
          fontSize="56"
        >
          ع
        </text>
      </svg>
      <span className="orbit-caption">LANGUAGE → EVIDENCE → CONFIDENCE</span>
      <div className="orbit-readout">
        <span>Observed regressions</span>
        <strong>{comparison ? comparison.counts.regressed : "—"}</strong>
        <small>
          {comparison
            ? "in your selected comparison"
            : "Run a comparison to measure"}
        </small>
      </div>
    </div>
  );
}
