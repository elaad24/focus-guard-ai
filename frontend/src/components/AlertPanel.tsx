import { useState } from "react";
import { dismissAlert } from "../api/settings";
import { StatusSnapshot } from "../types";

type AlertPanelProps = {
  status: StatusSnapshot;
};

export const AlertPanel = ({ status }: AlertPanelProps) => {
  const [dismissing, setDismissing] = useState(false);
  const alertActive = status.alert_active || status.state === "ALERT_ACTIVE";

  const handleDismiss = async () => {
    setDismissing(true);
    try {
      await dismissAlert();
    } finally {
      setDismissing(false);
    }
  };

  if (!alertActive) {
    return null;
  }

  return (
    <div className="alert-overlay" data-test-id="alert-panel">
      <div
        className="alert-modal alert-modal-cheerful"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="alert-title"
      >
        <p className="alert-kicker">Final check-in</p>
        <h2 id="alert-title">You've got this — time to refocus!</h2>
        <p>
          You've been distracted for {status.time_above_threshold_seconds.toFixed(0)} seconds. Take a
          breath, close distractions, and jump back in. The cheerful reminder plays until you confirm
          you're back.
        </p>
        <button
          type="button"
          className="primary-button"
          onClick={handleDismiss}
          disabled={dismissing}
          data-test-id="alert-dismiss-button"
        >
          {dismissing ? "Confirming..." : "I'm back — let's focus"}
        </button>
      </div>
    </div>
  );
};
