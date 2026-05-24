import { useEffect, useMemo, useState } from "react";
import { StatusSnapshot } from "../types";

type FocusScorePanelProps = {
  status: StatusSnapshot;
};

export const FocusScorePanel = ({ status }: FocusScorePanelProps) => {
  const [history, setHistory] = useState<Array<number>>([status.focus_score]);

  useEffect(() => {
    setHistory((prev) => {
      const next = [...prev, status.focus_score];
      return next.slice(-40);
    });
  }, [status.focus_score]);

  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.max(0, Math.min(100, status.focus_score));
  const dashOffset = circumference - (progress / 100) * circumference;

  const sparklinePoints = useMemo(() => {
    if (history.length === 0) {
      return "";
    }
    const width = 320;
    const height = 80;
    const max = Math.max(...history, 100);
    const min = Math.min(...history, 0);
    const range = Math.max(max - min, 1);

    return history
      .map((value, index) => {
        const x = (index / Math.max(history.length - 1, 1)) * width;
        const y = height - ((value - min) / range) * height;
        return `${x},${y}`;
      })
      .join(" ");
  }, [history]);

  return (
    <section className="panel span-6" data-test-id="focus-score-panel">
      <h2 className="panel-title">Focus Score</h2>
      <div className="focus-gauge">
        <svg width="180" height="180" viewBox="0 0 180 180" aria-hidden="true">
          <circle cx="90" cy="90" r={radius} fill="none" stroke="rgba(148,163,184,0.18)" strokeWidth="12" />
          <circle
            cx="90"
            cy="90"
            r={radius}
            fill="none"
            stroke="url(#focusGradient)"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
          />
          <defs>
            <linearGradient id="focusGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>
          </defs>
        </svg>
        <div className="focus-gauge-value">{status.focus_score}</div>
      </div>
      <div className="metric-card">
        <span className="metric-label">Distraction Score</span>
        <div className="progress-bar" style={{ marginTop: 8 }}>
          <div
            className={`progress-fill ${status.distraction_score >= 70 ? "danger" : ""}`}
            style={{ width: `${status.distraction_score}%` }}
          />
        </div>
        <span className="metric-value" style={{ marginTop: 8, display: "block" }}>
          {status.distraction_score} / 100
        </span>
      </div>
      <svg className="sparkline" viewBox="0 0 320 80" preserveAspectRatio="none" aria-hidden="true">
        <polyline
          fill="none"
          stroke="#38bdf8"
          strokeWidth="2"
          points={sparklinePoints}
        />
      </svg>
    </section>
  );
};
