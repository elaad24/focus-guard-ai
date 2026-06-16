import { StatusSnapshot } from "../types";

type WarningBannerProps = {
  status: StatusSnapshot;
};

const bannerCopy: Record<string, { title: string; message: string }> = {
  soft: {
    title: "Soft warning",
    message:
      "You've been distracted for a while. Listen for the gentle nudge sound or check your desktop notification.",
  },
  medium: {
    title: "Medium reminder",
    message: "Still off track. Listen for the positive chime and bring your attention back to your task.",
  },
  building: {
    title: "Distraction building",
    message: "Your distraction score is rising. Consider refocusing before the next warning stage.",
  },
};

const fatigueBannerCopy: Record<string, { title: string; message: string }> = {
  soft: {
    title: "Fatigue detected",
    message:
      "You seem tired — keep your eyes open for 20 seconds, stand and stretch, sip water, or take a 2-minute movement break.",
  },
  medium: {
    title: "Still tired",
    message:
      "Yawning or closed eyes are still showing up. Try cold water, a brisk walk, or switch to a lighter task for five minutes.",
  },
  building: {
    title: "Wake-up nudge",
    message:
      "Signs of sleepiness detected. A short break now can help you return to study with more focus.",
  },
};

export const WarningBanner = ({ status }: WarningBannerProps) => {
  const copySource = status.fatigue_active ? fatigueBannerCopy : bannerCopy;
  const copy = copySource[status.warning_stage];
  if (!copy) {
    return null;
  }

  return (
    <div
      className={`warning-banner warning-banner-${status.warning_stage} ${
        status.fatigue_active ? "warning-banner-fatigue" : ""
      }`}
      role="status"
      data-test-id="warning-banner"
    >
      <strong>{copy.title}</strong>
      <span>{copy.message}</span>
    </div>
  );
};
