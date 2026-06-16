export const distractionLabels: Record<string, string> = {
  phone_near_person: "Phone detected near you",
  phone_near_hand_or_face: "Phone near hand or face",
  phone_usage_over_limit: "Phone use exceeded time limit",
  head_looking_down: "Head looking down",
  looking_away_from_screen: "Looking away from screen",
  keyboard_mouse_idle: "No keyboard/mouse activity",
  body_hand_idle: "Hands not moving",
  frequent_yawns: "Repeated yawning (possible fatigue)",
  eyes_closed_too_long: "Eyes closed for extended period",
  no_person_detected: "Person not visible to camera",
  tablet_mode_reduction: "Tablet mode score reduction",
  high_distraction: "High distraction level",
  elevated_distraction: "Elevated distraction level",
  mild_distraction: "Mild distraction detected",
  person_not_visible: "Person not visible to camera",
  break_mode: "Break mode active",
};

export const warningStageLabels: Record<string, string> = {
  soft: "Soft",
  medium: "Medium",
  final: "Final",
  building: "Building",
  cooldown: "Cooldown",
  break: "Break",
};

export const labelContributor = (key: string): string =>
  distractionLabels[key] ?? key.replace(/_/g, " ");
