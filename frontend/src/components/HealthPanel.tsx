import { HealthResponse } from "../types";

type HealthPanelProps = {
  health: HealthResponse | null;
  connectionStatus: string;
  fps: number;
  mode: string;
};

const statusClass = (value: string) => (value === "ok" ? "on" : "off");

export const HealthPanel = ({ health, connectionStatus, fps, mode }: HealthPanelProps) => {
  const items = [
    { label: "Backend", value: health?.backend ?? "unknown" },
    { label: "Camera", value: health?.camera ?? "unknown" },
    { label: "YOLO Model", value: health?.model ?? "unknown" },
    { label: "Keyboard/Mouse", value: health?.keyboard_mouse ?? "unknown" },
    { label: "WebSocket", value: connectionStatus === "connected" ? "ok" : "error" },
    { label: "Alert System", value: health?.alert_system ?? "unknown" },
  ];

  return (
    <section className="panel span-6" data-test-id="health-panel">
      <h2 className="panel-title">System Health</h2>
      <div className="signal-list">
        {items.map((item) => (
          <div key={item.label} className="signal-item">
            <span>{item.label}</span>
            <span className="metric-value">
              <span className={`led ${statusClass(item.value)}`} /> {item.value}
            </span>
          </div>
        ))}
      </div>
      <div className="metric-grid" style={{ marginTop: 12 }}>
        <div className="metric-card">
          <span className="metric-label">Current FPS</span>
          <span className="metric-value">{fps.toFixed(1)}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Active Mode</span>
          <span className="metric-value">{mode}</span>
        </div>
      </div>
    </section>
  );
};
