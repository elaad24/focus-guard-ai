import { useCallback, useEffect, useRef, useState } from "react";
import { getState, setGazePose, setGazeProfile } from "../api/settings";
import { StatusSnapshot, WorkstationProfile } from "../types";

type SetupStep = "profile" | "pose" | "done";

type WorkstationSetupPanelProps = {
  isOpen: boolean;
  status: StatusSnapshot;
  cameraStreaming: boolean;
  onEnableCamera: () => void;
  onSendFrameNow: () => void;
  onComplete: () => void;
};

const PROFILE_OPTIONS: Array<{
  id: WorkstationProfile;
  title: string;
  description: string;
}> = [
  {
    id: "laptop_below",
    title: "Laptop below camera",
    description: "Camera is above the screen. Normal working posture looks slightly down.",
  },
  {
    id: "screens_in_front",
    title: "Screens in front",
    description: "Monitors face you directly. Camera is near the screen center.",
  },
  {
    id: "side_monitors",
    title: "Side monitors",
    description: "Primary screens are to your left or right of the camera.",
  },
];

const POSE_CAPTURE_SECONDS = 3;
const POSE_SAMPLE_INTERVAL_MS = 400;

export const WorkstationSetupPanel = ({
  isOpen,
  status,
  cameraStreaming,
  onEnableCamera,
  onSendFrameNow,
  onComplete,
}: WorkstationSetupPanelProps) => {
  const [step, setStep] = useState<SetupStep>("profile");
  const [selectedProfile, setSelectedProfile] = useState<WorkstationProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [countdown, setCountdown] = useState<number | null>(null);
  const [sampleCount, setSampleCount] = useState(0);
  const [calibrationSummary, setCalibrationSummary] = useState("");
  const samplesRef = useRef<Array<{ pitch: number; yaw: number }>>([]);
  const captureTimerRef = useRef<number | null>(null);

  const clearCaptureTimer = useCallback(() => {
    if (captureTimerRef.current !== null) {
      window.clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!isOpen) {
      setStep("profile");
      setSelectedProfile(null);
      setErrorMessage("");
      setCountdown(null);
      setSampleCount(0);
      setCalibrationSummary("");
      samplesRef.current = [];
      clearCaptureTimer();
    }
  }, [isOpen, clearCaptureTimer]);

  useEffect(() => {
    return () => clearCaptureTimer();
  }, [clearCaptureTimer]);

  const handleSelectProfile = async (profile: WorkstationProfile) => {
    setSaving(true);
    setErrorMessage("");
    try {
      await setGazeProfile(profile);
      setSelectedProfile(profile);
      setStep("pose");
    } catch {
      setErrorMessage("Failed to save workstation profile.");
    } finally {
      setSaving(false);
    }
  };

  const collectSample = useCallback(async () => {
    onSendFrameNow();
    try {
      const snapshot = await getState();
      if (snapshot.signals.person_detected) {
        samplesRef.current.push({
          pitch: snapshot.gaze_pitch,
          yaw: snapshot.gaze_yaw,
        });
        setSampleCount(samplesRef.current.length);
      }
    } catch {
      if (status.signals.person_detected) {
        samplesRef.current.push({
          pitch: status.gaze_pitch,
          yaw: status.gaze_yaw,
        });
        setSampleCount(samplesRef.current.length);
      }
    }
  }, [onSendFrameNow, status.gaze_pitch, status.gaze_yaw, status.signals.person_detected]);

  const finishPoseCapture = useCallback(async () => {
    const samples = samplesRef.current;
    if (samples.length === 0) {
      setErrorMessage("No face samples captured. Stay visible to the camera and try again.");
      return;
    }

    setSaving(true);
    setErrorMessage("");
    try {
      const result = await setGazePose(samples);
      const profileLabel =
        PROFILE_OPTIONS.find((option) => option.id === result.workstationProfile)?.title ??
        result.workstationProfile ??
        "Unknown";
      setCalibrationSummary(
        `${profileLabel} — baseline pitch ${result.baselinePitch?.toFixed(1)}, yaw ${result.baselineYaw?.toFixed(1)}`,
      );
      setStep("done");
    } catch {
      setErrorMessage("Failed to save pose calibration.");
    } finally {
      setSaving(false);
    }
  }, []);

  const handleStartPoseCapture = () => {
    if (!cameraStreaming) {
      setErrorMessage("Enable the camera first, then hold your normal working posture.");
      return;
    }

    setErrorMessage("");
    samplesRef.current = [];
    setSampleCount(0);
    setCountdown(POSE_CAPTURE_SECONDS);
    void collectSample();

    let remaining = POSE_CAPTURE_SECONDS;
    captureTimerRef.current = window.setInterval(() => {
      remaining -= 1;
      void collectSample();
      if (remaining <= 0) {
        clearCaptureTimer();
        setCountdown(null);
        void finishPoseCapture();
      } else {
        setCountdown(remaining);
      }
    }, POSE_SAMPLE_INTERVAL_MS);
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="alert-overlay setup-overlay" data-test-id="workstation-setup-modal">
      <div className="alert-modal alert-modal-cheerful setup-modal">
        <p className="alert-kicker">Workstation setup</p>
        <h2>Calibrate gaze for your desk</h2>
        <p className="event-meta setup-intro">
          Pick your layout, then hold your normal working posture for {POSE_CAPTURE_SECONDS}{" "}
          seconds so head/gaze detection matches how you actually sit.
        </p>

        <div className="stage-track setup-steps">
          <div className={`stage-step ${step === "profile" ? "active" : ""}`}>1. Layout</div>
          <div className={`stage-step ${step === "pose" ? "active" : ""}`}>2. Pose</div>
          <div className={`stage-step ${step === "done" ? "active" : ""}`}>3. Done</div>
        </div>

        {step === "profile" ? (
          <div className="setup-profile-grid" data-test-id="workstation-profile-step">
            {PROFILE_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                className={`setup-profile-card ${selectedProfile === option.id ? "active" : ""}`}
                onClick={() => handleSelectProfile(option.id)}
                disabled={saving}
                data-test-id={`workstation-profile-${option.id}`}
              >
                <strong>{option.title}</strong>
                <span>{option.description}</span>
              </button>
            ))}
          </div>
        ) : null}

        {step === "pose" ? (
          <div className="setup-pose-step" data-test-id="workstation-pose-step">
            {!cameraStreaming ? (
              <>
                <p>Camera must be enabled for pose capture.</p>
                <button
                  type="button"
                  className="primary-button"
                  onClick={onEnableCamera}
                  data-test-id="setup-enable-camera-button"
                >
                  Enable Camera
                </button>
              </>
            ) : (
              <>
                <p>Sit naturally at your desk and look at your main screen.</p>
                {countdown !== null ? (
                  <div className="setup-countdown" data-test-id="pose-countdown">
                    {countdown}
                  </div>
                ) : (
                  <button
                    type="button"
                    className="primary-button"
                    onClick={handleStartPoseCapture}
                    disabled={saving}
                    data-test-id="start-pose-capture-button"
                  >
                    {saving ? "Saving..." : "Start 3-second capture"}
                  </button>
                )}
                <p className="event-meta">
                  Samples: {sampleCount} · Pitch {status.gaze_pitch.toFixed(1)} · Yaw{" "}
                  {status.gaze_yaw.toFixed(1)}
                </p>
              </>
            )}
          </div>
        ) : null}

        {step === "done" ? (
          <div className="setup-done-step" data-test-id="workstation-done-step">
            <p>Calibration complete.</p>
            <p className="event-meta">{calibrationSummary}</p>
            <button
              type="button"
              className="primary-button"
              onClick={onComplete}
              data-test-id="setup-complete-button"
            >
              Start monitoring
            </button>
          </div>
        ) : null}

        {errorMessage ? <p className="event-meta setup-error">{errorMessage}</p> : null}
      </div>
    </div>
  );
};
