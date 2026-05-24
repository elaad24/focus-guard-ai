import { API_BASE, AppSettings, FocusMode, GazeCalibration, HealthResponse, SessionSummary, StatusSnapshot, WorkstationProfile } from "../types";

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
};

export const getHealth = () => request<HealthResponse>("/health");

export const getSettings = () => request<AppSettings>("/settings");

export const patchSettings = (partial: Partial<AppSettings>) =>
  request<AppSettings>("/settings", {
    method: "POST",
    body: JSON.stringify(partial),
  });

export const setMode = (mode: FocusMode) =>
  request<{ mode: FocusMode }>("/mode", {
    method: "POST",
    body: JSON.stringify({ mode }),
  });

export const dismissAlert = () =>
  request<{ dismissed: boolean }>("/alert/dismiss", {
    method: "POST",
  });

export const getSessionSummary = () => request<SessionSummary>("/session-summary");

export const resetSession = () =>
  request<SessionSummary>("/session/reset", {
    method: "POST",
  });

export const getState = () => request<StatusSnapshot>("/state");

export const getGazeCalibration = () => request<GazeCalibration>("/calibration/gaze");

export const setGazeProfile = (workstationProfile: WorkstationProfile) =>
  request<GazeCalibration>("/calibration/gaze/profile", {
    method: "POST",
    body: JSON.stringify({ workstationProfile }),
  });

export const setGazePose = (samples: Array<{ pitch: number; yaw: number }>) =>
  request<GazeCalibration>("/calibration/gaze/pose", {
    method: "POST",
    body: JSON.stringify({ samples }),
  });

export const resetGazeCalibration = () =>
  request<GazeCalibration>("/calibration/gaze/reset", {
    method: "POST",
  });

export const calibrateScreenZone = (zone: { x1: number; y1: number; x2: number; y2: number }) =>
  request<{ x1: number; y1: number; x2: number; y2: number }>("/calibration/screen-zone", {
    method: "POST",
    body: JSON.stringify(zone),
  });

export const submitCameraFrame = async (frame: Blob) => {
  const response = await fetch(`${API_BASE}/camera/frame`, {
    method: "POST",
    headers: {
      "Content-Type": "image/jpeg",
    },
    body: frame,
  });

  if (!response.ok) {
    throw new Error(`Camera frame upload failed: ${response.status}`);
  }

  return response.json() as Promise<{ accepted: boolean }>;
};
