import { useEffect } from "react";
import { useBrowserCamera } from "../hooks/useBrowserCamera";
import { FocusMode } from "../types";

type CameraPreviewPanelProps = {
  cameraOk: boolean;
  mode: FocusMode;
  onControlsReady?: (controls: {
    sendFrameNow: () => void;
    enableCamera: () => void;
    isStreaming: boolean;
  }) => void;
};

export const CameraPreviewPanel = ({ cameraOk, mode, onControlsReady }: CameraPreviewPanelProps) => {
  const { videoRef, canvasRef, status, errorMessage, framesSent, handleEnableCamera, sendFrameNow } =
    useBrowserCamera({ mode });

  const isStreaming = status === "streaming";
  const uploadsPaused = mode === "break";

  useEffect(() => {
    onControlsReady?.({
      sendFrameNow: () => {
        void sendFrameNow();
      },
      enableCamera: handleEnableCamera,
      isStreaming,
    });
  }, [onControlsReady, sendFrameNow, handleEnableCamera, isStreaming]);

  return (
    <section className="panel span-6" data-test-id="camera-preview-panel">
      <h2 className="panel-title">Live Camera (Browser)</h2>
      <p className="event-meta" style={{ marginBottom: 12 }}>
        The camera opens in Chrome with a normal permission prompt. One frame is sent to your local
        backend every 5 seconds for detection — the live preview stays real-time in the browser.
      </p>
      <p className="event-meta privacy-note" style={{ marginBottom: 12 }}>
        Privacy: camera frames are processed in memory only and are never saved to disk, cloud, or
        browser storage.
      </p>

      {uploadsPaused ? (
        <p className="event-meta" data-test-id="break-camera-paused">
          Break mode: frame uploads and detection are paused to save resources.
        </p>
      ) : null}

      {status === "idle" || status === "denied" || status === "error" ? (
        <button
          type="button"
          className="primary-button"
          onClick={handleEnableCamera}
          data-test-id="enable-camera-button"
        >
          Enable Camera
        </button>
      ) : null}

      {status === "requesting" ? <p className="event-meta">Requesting camera access...</p> : null}
      {errorMessage ? <p className="event-meta">{errorMessage}</p> : null}

      <div className="camera-preview-wrapper">
        <video
          ref={videoRef}
          className="camera-preview-image"
          autoPlay
          playsInline
          muted
          data-test-id="camera-preview-video"
          style={{ display: isStreaming ? "block" : "none" }}
        />
        {isStreaming ? (
          <div className="camera-detection-frame" aria-hidden="true" data-test-id="detection-frame-overlay">
            <span className="camera-detection-frame-label">Detection zone</span>
          </div>
        ) : null}
      </div>
      <canvas ref={canvasRef} hidden aria-hidden="true" />

      {!isStreaming && status !== "requesting" ? (
        <p className="event-meta">
          Click Enable Camera to allow Chrome access. Position your desk and phone inside the
          detection frame guide.
        </p>
      ) : null}

      <div className="metric-grid" style={{ marginTop: 12 }}>
        <div className="metric-card">
          <span className="metric-label">Upload Interval</span>
          <span className="metric-value">{uploadsPaused ? "paused" : "5s"}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Camera Status</span>
          <span className="metric-value">{cameraOk ? "streaming" : status}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Frames Sent</span>
          <span className="metric-value">{framesSent}</span>
        </div>
      </div>
    </section>
  );
};
