import { useEffect, useState } from "react";
import { getHealth } from "./api/settings";
import { useStatus } from "./api/websocket";
import { AlertPanel } from "./components/AlertPanel";
import { CameraPreviewPanel } from "./components/CameraPreviewPanel";
import { DetectionSignalsPanel } from "./components/DetectionSignalsPanel";
import { EventLogPanel } from "./components/EventLogPanel";
import { FocusScorePanel } from "./components/FocusScorePanel";
import { HealthPanel } from "./components/HealthPanel";
import { LiveStatusPanel } from "./components/LiveStatusPanel";
import { ModesPanel } from "./components/ModesPanel";
import { SessionSummaryPanel } from "./components/SessionSummaryPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { WarningBanner } from "./components/WarningBanner";
import { HealthResponse } from "./types";

const HEALTH_POLL_INTERVAL_MS = 30_000;

const App = () => {
  const { status, connectionStatus } = useStatus();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await getHealth();
        setHealth(response);
      } catch {
        setHealth(null);
      }
    };

    fetchHealth();
    const interval = window.setInterval(fetchHealth, HEALTH_POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <div className="app-shell" data-test-id="focus-guard-app">
      <header className="app-header">
        <div>
          <h1 className="app-title">Focus Guard AI</h1>
          <p className="app-subtitle">Local distraction monitoring and alert system</p>
        </div>
        <div className="header-chips">
          <span className={`chip ${connectionStatus === "connected" ? "connected" : "disconnected"}`}>
            WebSocket: {connectionStatus}
          </span>
          <span className="chip">Mode: {status.mode}</span>
          <span className="chip">Focus: {status.focus_score}</span>
        </div>
      </header>

      <WarningBanner status={status} />

      <main className="dashboard-grid">
        <HealthPanel
          health={health}
          connectionStatus={connectionStatus}
          fps={status.fps}
          mode={status.mode}
        />
        <CameraPreviewPanel cameraOk={status.camera_ok} />
        <LiveStatusPanel status={status} />
        <FocusScorePanel status={status} />
        <DetectionSignalsPanel signals={status.signals} />
        <ModesPanel currentMode={status.mode} />
        <SettingsPanel />
        <SessionSummaryPanel summary={status.session_summary} />
        <EventLogPanel events={status.events} />
      </main>

      <AlertPanel status={status} />
    </div>
  );
};

export default App;
