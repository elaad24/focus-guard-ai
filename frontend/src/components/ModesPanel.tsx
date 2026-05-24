import { useState } from "react";
import { setMode } from "../api/settings";
import { FocusMode } from "../types";

type ModesPanelProps = {
  currentMode: FocusMode;
};

const modes: Array<{ id: FocusMode; label: string; description: string }> = [
  { id: "normal", label: "Normal", description: "Standard distraction rules" },
  { id: "video_lesson", label: "Video Lesson", description: "Passive viewing allowed, phone still suspicious" },
  { id: "ipad", label: "iPad", description: "Tablet usage allowed, phone still suspicious" },
  { id: "break", label: "Break", description: "Alerts disabled, passive monitoring only" },
];

export const ModesPanel = ({ currentMode }: ModesPanelProps) => {
  const [loadingMode, setLoadingMode] = useState<FocusMode | null>(null);
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
      {error ? <p className="event-meta">{error}</p> : null}
    </section>
  );
};
