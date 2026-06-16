import { useState } from "react";
import { cancelSnooze, setMode, startSnooze } from "../api/settings";
import { FocusMode, StatusSnapshot } from "../types";

type ModesPanelProps = {
  currentMode: FocusMode;
  status: StatusSnapshot;
};

const modes: Array<{ id: FocusMode; label: string; description: string }> = [
  { id: "normal", label: "Normal", description: "Standard distraction rules" },
  { id: "video_lesson", label: "Video Lesson", description: "Passive viewing allowed, phone still suspicious" },
  { id: "ipad", label: "iPad", description: "Tablet usage allowed, phone still suspicious" },
  {
    id: "reading_meeting",
    label: "Reading / Meeting",
    description: "Head-down and looking-away ignored; phone still suspicious",
  },
  { id: "break", label: "Break", description: "Alerts disabled, passive monitoring only" },
];

const snoozeOptions = [
  { label: "15 min", seconds: 15 * 60 },
  { label: "25 min", seconds: 25 * 60 },
  { label: "60 min", seconds: 60 * 60 },
];

export const ModesPanel = ({ currentMode, status }: ModesPanelProps) => {
  const [loadingMode, setLoadingMode] = useState<FocusMode | null>(null);
  const [snoozeDuration, setSnoozeDuration] = useState(snoozeOptions[1].seconds);
  const [snoozeLoading, setSnoozeLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSelectMode = async (mode: FocusMode) => {
    setLoadingMode(mode);
    setError("");
    try {
      await setMode(mode);
    } catch {
      setError("Failed to change mode");
    } finally {
      setLoadingMode(null);
    }
  };

  const handleStartSnooze = async () => {
    setSnoozeLoading(true);
    setError("");
    try {
      await startSnooze(snoozeDuration);
    } catch {
      setError("Failed to start snooze");
    } finally {
      setSnoozeLoading(false);
    }
  };

  const handleCancelSnooze = async () => {
    setSnoozeLoading(true);
    setError("");
    try {
      await cancelSnooze();
    } catch {
      setError("Failed to cancel snooze");
    } finally {
      setSnoozeLoading(false);
    }
  };

  const formatRemaining = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <section className="panel span-6" data-test-id="modes-panel">
      <h2 className="panel-title">Modes</h2>
      <div className="mode-grid">
        {modes.map((mode) => (
          <button
            key={mode.id}
            type="button"
            className={`mode-button ${currentMode === mode.id ? "active" : ""}`}
            onClick={() => handleSelectMode(mode.id)}
            disabled={loadingMode !== null}
            data-test-id={`mode-button-${mode.id}`}
          >
            <strong>{mode.label}</strong>
            <div className="event-meta">{mode.description}</div>
          </button>
        ))}
      </div>
      {currentMode === "break" ? (
        <p style={{ marginTop: 12, color: "#a78bfa" }}>Break mode active</p>
      ) : null}
      {currentMode === "reading_meeting" ? (
        <p style={{ marginTop: 12, color: "#34d399" }}>Reading / meeting mode active</p>
      ) : null}

      <div className="settings-workstation-section" style={{ marginTop: 16 }}>
        <h3 className="settings-section-title">Snooze alerts</h3>
        {status.snooze_active ? (
          <>
            <p className="event-meta" data-test-id="snooze-active-label">
              Snooze active — {formatRemaining(status.snooze_remaining_seconds)} remaining
            </p>
            <button
              type="button"
              className="secondary-button"
              onClick={handleCancelSnooze}
              disabled={snoozeLoading}
              data-test-id="snooze-cancel-button"
            >
              {snoozeLoading ? "Cancelling..." : "Cancel snooze"}
            </button>
          </>
        ) : (
          <>
            <p className="event-meta">
              Temporarily suppress all alerts. Monitoring continues; alerts resume when snooze ends.
            </p>
            <div className="field" style={{ marginTop: 8 }}>
              <label htmlFor="snoozeDuration">Duration</label>
              <select
                id="snoozeDuration"
                value={snoozeDuration}
                onChange={(event) => setSnoozeDuration(Number(event.target.value))}
                data-test-id="snooze-duration-select"
              >
                {snoozeOptions.map((option) => (
                  <option key={option.seconds} value={option.seconds}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="primary-button"
              onClick={handleStartSnooze}
              disabled={snoozeLoading}
              data-test-id="snooze-start-button"
            >
              {snoozeLoading ? "Starting..." : "Start snooze"}
            </button>
          </>
        )}
      </div>

      {error ? <p className="event-meta">{error}</p> : null}
    </section>
  );
};
