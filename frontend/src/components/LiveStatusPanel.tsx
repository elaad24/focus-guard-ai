import { StatusSnapshot } from "../types";

type LiveStatusPanelProps = {
  status: StatusSnapshot;
};

const stateClass = (state: string) => {
  if (state === "FOCUSED") return "focused";
  if (state === "DISTRACTION_WARNING_SOFT") return "warning-soft";
  if (state === "DISTRACTION_WARNING_MEDIUM") return "warning-medium";
  if (state === "ALERT_ACTIVE") return "alert";
  if (state === "BREAK_MODE") return "break";
  if (state === "SNOOZED") return "break";
  return "distracted";
};

export const LiveStatusPanel = ({ status }: LiveStatusPanelProps) => {
  const stageLabels = ["Soft (45s)", "Medium (60s)", "Final (90s)"];
  const activeStageIndex =
    status.warning_stage === "soft"
      ? 0
      : status.warning_stage === "medium"
        ? 1
        : status.warning_stage === "final"
          ? 2
          : -1;

  return (
    <section className="panel span-6" data-test-id="live-status-panel">
      <h2 className="panel-title">Live Status</h2>
      <div className={`status-badge ${stateClass(status.state)}`}>{status.state}</div>
      <div className="metric-grid" style={{ marginTop: 14 }}>
        <div className="metric-card">
          <span className="metric-label">Focus Score</span>
          <span className="metric-value">{status.focus_score}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Distraction Score</span>
          <span className="metric-value">{status.distraction_score}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Time Above Threshold</span>
          <span className="metric-value">{status.time_above_threshold_seconds.toFixed(1)}s</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Keyboard/Mouse Idle</span>
          <span className="metric-value">{status.keyboard_mouse_idle_seconds.toFixed(1)}s</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Warning Stage</span>
          <span className="metric-value">{status.warning_stage}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Cooldown Remaining</span>
          <span className="metric-value">{status.cooldown_remaining_seconds.toFixed(1)}s</span>
        </div>
      </div>
      <div className="stage-track" style={{ marginTop: 14 }}>
        {stageLabels.map((label, index) => (
          <div key={label} className={`stage-step ${activeStageIndex === index ? "active" : ""}`}>
            {label}
          </div>
        ))}
      </div>
    </section>
  );
};
