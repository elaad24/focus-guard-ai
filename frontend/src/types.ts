export type FocusMode = "normal" | "video_lesson" | "ipad" | "break" | "reading_meeting";

export type FocusState =
  | "FOCUSED"
  | "DISTRACTED"
  | "DISTRACTION_WARNING_SOFT"
  | "DISTRACTION_WARNING_MEDIUM"
  | "ALERT_ACTIVE"
  | "DISMISSED_COOLDOWN"
  | "BREAK_MODE"
  | "SNOOZED";

export type DetectionSignals = {
  person_detected: boolean;
  phone_detected: boolean;
  phone_near_person: boolean;
  phone_near_hand_or_face: boolean;
  head_looking_down: boolean;
  looking_away_from_screen: boolean;
  keyboard_mouse_idle: boolean;
  body_hand_idle: boolean;
  tablet_detected: boolean;
  tablet_near_person: boolean;
  tablet_mode_active: boolean;
  break_mode_active: boolean;
  video_lesson_mode_active: boolean;
  eyes_closed: boolean;
  frequent_yawns: boolean;
  eyes_closed_too_long: boolean;
};

export type SessionSummary = {
  session_start_time: number;
  total_monitored_seconds: number;
  focused_time_seconds: number;
  distracted_time_seconds: number;
  soft_warnings: number;
  medium_warnings: number;
  final_alerts: number;
  dismissals: number;
  total_phone_detected_seconds: number;
  longest_focused_streak_seconds: number;
  longest_distraction_streak_seconds: number;
  most_common_trigger: string;
};

export type StatusEvent = {
  type: string;
  message: string;
  timestamp: number;
  contributors?: Array<string>;
  warning_stage?: string;
};

export type StatusSnapshot = {
  state: FocusState;
  mode: FocusMode;
  focus_score: number;
  distraction_score: number;
  distraction_contributors: Array<string>;
  focus_contributors: Array<string>;
  signals: DetectionSignals;
  keyboard_mouse_idle_seconds: number;
  time_above_threshold_seconds: number;
  warning_stage: string;
  alert_active: boolean;
  cooldown_remaining_seconds: number;
  fps: number;
  camera_ok: boolean;
  model_ok: boolean;
  kb_mouse_ok: boolean;
  alert_system_ok: boolean;
  active_window: { app_name: string; bundle_id: string };
  session_summary: SessionSummary;
  events: Array<StatusEvent>;
  gaze_pitch: number;
  gaze_yaw: number;
  gaze_calibrated: boolean;
  workstation_profile: WorkstationProfile | null;
  recent_input_activity: boolean;
  input_activity_override_active: boolean;
  fatigue_active: boolean;
  snooze_active: boolean;
  snooze_remaining_seconds: number;
};

export type WorkstationProfile = "laptop_below" | "screens_in_front" | "side_monitors";

export type GazeCalibration = {
  calibrated: boolean;
  workstationProfile: WorkstationProfile | null;
  baselinePitch: number | null;
  baselineYaw: number | null;
  calibratedAt: number | null;
  focusZone: { x1: number; y1: number; x2: number; y2: number } | null;
};

export type AppSettings = {
  mode: FocusMode;
  softWarningAfterSeconds: number;
  mediumWarningAfterSeconds: number;
  finalAlertAfterSeconds: number;
  phoneUsageLimitSeconds: number;
  keyboardMouseIdleLimitSeconds: number;
  procrastinationScoreThreshold: number;
  cooldownAfterDismissSeconds: number;
  inputActivityFocusWindowSeconds: number;
  soundEnabled: boolean;
  notificationsEnabled: boolean;
};

export type HealthResponse = {
  backend: string;
  camera: string;
  model: string;
  keyboard_mouse: string;
  websocket: string;
  alert_system: string;
  fps: number;
  mode: string;
  backend_cpu_percent?: number | null;
  backend_memory_mb?: number | null;
};

const backendPort = import.meta.env.VITE_FOCUS_GUARD_PORT ?? "8787";

export const API_BASE = import.meta.env.DEV ? "/api" : `http://127.0.0.1:${backendPort}`;

const wsProtocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
const wsHost =
  typeof window !== "undefined" && import.meta.env.DEV
    ? window.location.host
    : `127.0.0.1:${backendPort}`;

export const WS_URL = `${wsProtocol}//${wsHost}/ws/status`;

export const DEFAULT_STATUS: StatusSnapshot = {
  state: "FOCUSED",
  mode: "normal",
  focus_score: 85,
  distraction_score: 0,
  distraction_contributors: [],
  focus_contributors: [],
  signals: {
    person_detected: false,
    phone_detected: false,
    phone_near_person: false,
    phone_near_hand_or_face: false,
    head_looking_down: false,
    looking_away_from_screen: false,
    keyboard_mouse_idle: false,
    body_hand_idle: false,
    tablet_detected: false,
    tablet_near_person: false,
    tablet_mode_active: false,
    break_mode_active: false,
    video_lesson_mode_active: false,
    eyes_closed: false,
    frequent_yawns: false,
    eyes_closed_too_long: false,
  },
  keyboard_mouse_idle_seconds: 0,
  time_above_threshold_seconds: 0,
  warning_stage: "none",
  alert_active: false,
  cooldown_remaining_seconds: 0,
  fps: 0,
  camera_ok: false,
  model_ok: false,
  kb_mouse_ok: false,
  alert_system_ok: false,
  active_window: { app_name: "unknown", bundle_id: "unknown" },
  session_summary: {
    session_start_time: Date.now() / 1000,
    total_monitored_seconds: 0,
    focused_time_seconds: 0,
    distracted_time_seconds: 0,
    soft_warnings: 0,
    medium_warnings: 0,
    final_alerts: 0,
    dismissals: 0,
    total_phone_detected_seconds: 0,
    longest_focused_streak_seconds: 0,
    longest_distraction_streak_seconds: 0,
    most_common_trigger: "none",
  },
  events: [],
  gaze_pitch: 0,
  gaze_yaw: 0,
  gaze_calibrated: false,
  workstation_profile: null,
  recent_input_activity: false,
  input_activity_override_active: false,
  fatigue_active: false,
  snooze_active: false,
  snooze_remaining_seconds: 0,
};
