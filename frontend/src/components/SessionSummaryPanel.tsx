import { useState } from "react";
import { resetSession } from "../api/settings";
import { SessionSummary } from "../types";

type SessionSummaryPanelProps = {
  summary: SessionSummary;
};

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}m ${secs}s`;
};

export const SessionSummaryPanel = ({ summary }: SessionSummaryPanelProps) => {
  const [resetting, setResetting] = useState(false);

  const handleReset = async () => {
    setResetting(true);
    try {
      await resetSession();
    } finally {
      setResetting(false);
    }
  };

  const metrics = [
    { label: "Session start", value: new Date(summary.session_start_time * 1000).toLocaleTimeString() },
    { label: "Total monitored", value: formatDuration(summary.total_monitored_seconds) },
    { label: "Focused time", value: formatDuration(summary.focused_time_seconds) },
    { label: "Distracted time", value: formatDuration(summary.distracted_time_seconds) },
    { label: "Soft warnings", value: String(summary.soft_warnings) },
    { label: "Medium warnings", value: String(summary.medium_warnings) },
    { label: "Final alerts", value: String(summary.final_alerts) },
    { label: "Dismissals", value: String(summary.dismissals) },
    { label: "Phone detected time", value: formatDuration(summary.total_phone_detected_seconds) },
    { label: "Longest focus streak", value: formatDuration(summary.longest_focused_streak_seconds) },
    { label: "Longest distraction streak", value: formatDuration(summary.longest_distraction_streak_seconds) },
    { label: "Most common trigger", value: summary.most_common_trigger },
  ];

  return (
    <section className="panel span-6" data-test-id="session-summary-panel">
      <h2 className="panel-title">Session Summary</h2>
      <div className="metric-grid">
        {metrics.map((metric) => (
          <div key={metric.label} className="metric-card">
            <span className="metric-label">{metric.label}</span>
            <span className="metric-value">{metric.value}</span>
          </div>
        ))}
      </div>
      <button
        type="button"
        className="secondary-button"
        onClick={handleReset}
        disabled={resetting}
        data-test-id="session-reset-button"
      >
        {resetting ? "Resetting..." : "Reset Session"}
      </button>
    </section>
  );
};
