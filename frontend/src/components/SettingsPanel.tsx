import { useEffect, useState } from "react";
import { getSettings, patchSettings, resetGazeCalibration } from "../api/settings";
import { AppSettings } from "../types";

type SettingsPanelProps = {
  onRecalibrate?: () => void;
  gazeCalibrated?: boolean;
};

export const SettingsPanel = ({ onRecalibrate, gazeCalibrated = false }: SettingsPanelProps) => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [recalibrating, setRecalibrating] = useState(false);

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch(() => setMessage("Failed to load settings"));
  }, []);

  const handleChange = (key: keyof AppSettings, value: number | boolean) => {
    if (!settings) {
      return;
    }
    setSettings({ ...settings, [key]: value });
  };

  const handleSave = async () => {
    if (!settings) {
      return;
    }
    setSaving(true);
    setMessage("");
    try {
      const updated = await patchSettings(settings);
      setSettings(updated);
      setMessage("Settings saved");
    } catch {
      setMessage("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleRecalibrate = async () => {
    setRecalibrating(true);
    setMessage("");
    try {
      await resetGazeCalibration();
      setMessage("Calibration reset. Complete the setup wizard to recalibrate.");
      onRecalibrate?.();
    } catch {
      setMessage("Failed to reset calibration.");
    } finally {
      setRecalibrating(false);
    }
  };

  if (!settings) {
    return (
      <section className="panel span-6" data-test-id="settings-panel">
        <h2 className="panel-title">Settings</h2>
        <p>Loading settings...</p>
      </section>
    );
  }

  return (
    <section className="panel span-6" data-test-id="settings-panel">
      <h2 className="panel-title">Settings</h2>
      <div className="settings-workstation-section">
        <h3 className="settings-section-title">Workstation setup</h3>
        <p className="event-meta">
          {gazeCalibrated
            ? "Gaze calibration is active for your desk layout."
            : "Gaze calibration is not complete — run setup to improve accuracy."}
        </p>
        <button
          type="button"
          className="secondary-button"
          onClick={handleRecalibrate}
          disabled={recalibrating}
          data-test-id="recalibrate-gaze-button"
        >
          {recalibrating ? "Resetting..." : "Recalibrate workstation"}
        </button>
      </div>
      <div className="settings-grid">
        <div className="field">
          <label htmlFor="softWarningAfterSeconds">Soft warning (seconds)</label>
          <input
            id="softWarningAfterSeconds"
            type="number"
            value={settings.softWarningAfterSeconds}
            onChange={(event) => handleChange("softWarningAfterSeconds", Number(event.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="mediumWarningAfterSeconds">Medium warning (seconds)</label>
          <input
            id="mediumWarningAfterSeconds"
            type="number"
            value={settings.mediumWarningAfterSeconds}
            onChange={(event) => handleChange("mediumWarningAfterSeconds", Number(event.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="finalAlertAfterSeconds">Final alert (seconds)</label>
          <input
            id="finalAlertAfterSeconds"
            type="number"
            value={settings.finalAlertAfterSeconds}
            onChange={(event) => handleChange("finalAlertAfterSeconds", Number(event.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="phoneUsageLimitSeconds">Phone usage limit (seconds)</label>
          <input
            id="phoneUsageLimitSeconds"
            type="number"
            value={settings.phoneUsageLimitSeconds}
            onChange={(event) => handleChange("phoneUsageLimitSeconds", Number(event.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="keyboardMouseIdleLimitSeconds">Keyboard/mouse idle limit (seconds)</label>
          <input
            id="keyboardMouseIdleLimitSeconds"
            type="number"
            value={settings.keyboardMouseIdleLimitSeconds}
            onChange={(event) =>
              handleChange("keyboardMouseIdleLimitSeconds", Number(event.target.value))
            }
          />
        </div>
        <div className="field">
          <label htmlFor="procrastinationScoreThreshold">Distraction threshold</label>
          <input
            id="procrastinationScoreThreshold"
            type="number"
            value={settings.procrastinationScoreThreshold}
            onChange={(event) =>
              handleChange("procrastinationScoreThreshold", Number(event.target.value))
            }
          />
        </div>
        <div className="field">
          <label htmlFor="inputActivityFocusWindowSeconds">Input activity focus window (seconds)</label>
          <input
            id="inputActivityFocusWindowSeconds"
            type="number"
            value={settings.inputActivityFocusWindowSeconds ?? 10}
            onChange={(event) =>
              handleChange("inputActivityFocusWindowSeconds", Number(event.target.value))
            }
          />
        </div>
        <div className="field">
          <label htmlFor="cooldownAfterDismissSeconds">Cooldown after dismiss (seconds)</label>
          <input
            id="cooldownAfterDismissSeconds"
            type="number"
            value={settings.cooldownAfterDismissSeconds}
            onChange={(event) =>
              handleChange("cooldownAfterDismissSeconds", Number(event.target.value))
            }
          />
        </div>
      </div>
      <div style={{ marginTop: 12 }}>
        <div className="toggle-row">
          <span>Sound enabled</span>
          <input
            type="checkbox"
            checked={settings.soundEnabled}
            onChange={(event) => handleChange("soundEnabled", event.target.checked)}
          />
        </div>
        <div className="toggle-row">
          <span>Notifications enabled</span>
          <input
            type="checkbox"
            checked={settings.notificationsEnabled}
            onChange={(event) => handleChange("notificationsEnabled", event.target.checked)}
          />
        </div>
        <div className="toggle-row">
          <span>Debug mode</span>
          <input
            type="checkbox"
            checked={settings.debugMode}
            onChange={(event) => handleChange("debugMode", event.target.checked)}
          />
        </div>
      </div>
      <button
        type="button"
        className="primary-button"
        onClick={handleSave}
        disabled={saving}
        data-test-id="settings-save-button"
      >
        {saving ? "Saving..." : "Save Settings"}
      </button>
      {message ? <p className="event-meta">{message}</p> : null}
    </section>
  );
};
