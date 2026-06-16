import { useCallback, useEffect, useRef, useState } from "react";
import { getGazeCalibration } from "./api/settings";
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
import { WorkstationSetupPanel } from "./components/WorkstationSetupPanel";
import { useResourceUsage } from "./hooks/useResourceUsage";
type CameraControls = {
  sendFrameNow: () => void;
  enableCamera: () => void;
  isStreaming: boolean;
};

const App = () => {
  const { status, connectionStatus } = useStatus();
  const [showSetupWizard, setShowSetupWizard] = useState(false);
  const [cameraStreaming, setCameraStreaming] = useState(false);
  const cameraControlsRef = useRef<CameraControls>({
    sendFrameNow: () => {},
    enableCamera: () => {},
    isStreaming: false,
  });
  const resources = useResourceUsage();

  useEffect(() => {
    getGazeCalibration()
      .then((calibration) => {
        if (!calibration.calibrated) {
          setShowSetupWizard(true);
        }
      })
      .catch(() => {
        setShowSetupWizard(true);
      });
  }, []);

  const handleCameraControlsReady = useCallback((controls: CameraControls) => {
    cameraControlsRef.current = controls;
    setCameraStreaming(controls.isStreaming);
  }, []);

  const handleSetupComplete = () => {
    setShowSetupWizard(false);
  };

  const handleRecalibrate = () => {
    setShowSetupWizard(true);
  };

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
          {status.gaze_calibrated ? (
            <span className="chip" data-test-id="gaze-calibrated-chip">
              Gaze: calibrated
            </span>
          ) : (
            <span className="chip">Gaze: not calibrated</span>
          )}
          <span className="chip resource-chip" data-test-id="resource-be-cpu">
            BE CPU: {resources.backendCpuPercent !== null ? `${resources.backendCpuPercent}%` : "N/A"}
          </span>
          <span className="chip resource-chip" data-test-id="resource-be-mem">
            BE RAM: {resources.backendMemoryMb !== null ? `${resources.backendMemoryMb}MB` : "N/A"}
          </span>
          <span className="chip resource-chip" data-test-id="resource-fe-mem">
            FE RAM: {resources.frontendMemoryMb !== null ? `${resources.frontendMemoryMb}MB` : "N/A"}
          </span>
        </div>
      </header>

      <WarningBanner status={status} />

      <main className="dashboard-grid">
        <HealthPanel
          health={resources.health}
          connectionStatus={connectionStatus}
          fps={status.fps}
          mode={status.mode}
        />
        <CameraPreviewPanel
          cameraOk={status.camera_ok}
          mode={status.mode}
          onControlsReady={handleCameraControlsReady}
        />
        <LiveStatusPanel status={status} />
        <FocusScorePanel status={status} />
        <DetectionSignalsPanel
          signals={status.signals}
          inputActivityOverrideActive={status.input_activity_override_active}
        />
        <ModesPanel currentMode={status.mode} />
        <SettingsPanel onRecalibrate={handleRecalibrate} gazeCalibrated={status.gaze_calibrated} />
        <SessionSummaryPanel summary={status.session_summary} />
        <EventLogPanel events={status.events} />
      </main>

      <AlertPanel status={status} />

      <WorkstationSetupPanel
        isOpen={showSetupWizard}
        status={status}
        cameraStreaming={cameraStreaming}
        onEnableCamera={() => cameraControlsRef.current.enableCamera()}
        onSendFrameNow={() => cameraControlsRef.current.sendFrameNow()}
        onComplete={handleSetupComplete}
      />
    </div>
  );
};

export default App;
