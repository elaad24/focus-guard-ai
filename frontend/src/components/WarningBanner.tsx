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

export const WarningBanner = ({ status }: WarningBannerProps) => {
  const copy = bannerCopy[status.warning_stage];
  if (!copy) {
    return null;
  }

  return (
    <div
      className={`warning-banner warning-banner-${status.warning_stage}`}
      role="status"
      data-test-id="warning-banner"
    >
      <strong>{copy.title}</strong>
      <span>{copy.message}</span>
    </div>
  );
};
