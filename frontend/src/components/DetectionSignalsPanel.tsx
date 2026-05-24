import { DetectionSignals } from "../types";

type DetectionSignalsPanelProps = {
  signals: DetectionSignals;
  inputActivityOverrideActive?: boolean;
};

const signalLabels: Array<{ key: keyof DetectionSignals; label: string }> = [
  { key: "person_detected", label: "Person detected" },
  { key: "phone_detected", label: "Phone detected" },
  { key: "phone_near_person", label: "Phone near person" },
  { key: "phone_near_hand_or_face", label: "Phone near hand/face" },
  { key: "head_looking_down", label: "Head looking down" },
  { key: "looking_away_from_screen", label: "Looking away from screen" },
  { key: "keyboard_mouse_idle", label: "Keyboard/mouse idle" },
  { key: "body_hand_idle", label: "Body/hand idle" },
  { key: "tablet_detected", label: "Tablet detected" },
  { key: "tablet_near_person", label: "Tablet near person" },
  { key: "tablet_mode_active", label: "Tablet mode active" },
  { key: "break_mode_active", label: "Break mode active" },
  { key: "video_lesson_mode_active", label: "Video lesson mode active" },
];

export const DetectionSignalsPanel = ({
  signals,
  inputActivityOverrideActive = false,
}: DetectionSignalsPanelProps) => {
  return (
    <section className="panel span-6" data-test-id="detection-signals-panel">
      <h2 className="panel-title">Detection Signals</h2>
      {inputActivityOverrideActive ? (
        <div className="input-override-badge" data-test-id="input-activity-override-badge">
          Input activity — gaze/idle ignored
        </div>
      ) : null}
      <div className="signal-list">
        {signalLabels.map((item) => (
          <div key={item.key} className="signal-item">
            <span>{item.label}</span>
            <span className={`led ${signals[item.key] ? "on" : "off"}`} />
          </div>
        ))}
      </div>
    </section>
  );
};
