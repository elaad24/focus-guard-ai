import { useEffect, useState } from "react";
import { getSessionHistory } from "../api/settings";
import { labelContributor } from "../lib/contributorLabels";

type HistorySession = {
  id: number;
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
  ended_at: number;
  ended_reason: string;
};

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}m ${secs}s`;
};

export const SessionHistoryPanel = () => {
  const [sessions, setSessions] = useState<Array<HistorySession>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await getSessionHistory(10);
        setSessions(response.sessions as Array<HistorySession>);
      } catch {
        setError("Failed to load session history");
      } finally {
        setLoading(false);
      }
    };

    void loadHistory();
  }, []);

  return (
    <section className="panel span-6" data-test-id="session-history-panel">
      <h2 className="panel-title">Session History</h2>
      {loading ? <p className="event-meta">Loading history...</p> : null}
      {error ? <p className="event-meta">{error}</p> : null}
      {!loading && !error && sessions.length === 0 ? (
        <p className="event-meta">No saved sessions yet. History is recorded when you reset a session or shut down the backend.</p>
      ) : null}
      {!loading && sessions.length > 0 ? (
        <div className="event-log">
          {sessions.map((session) => (
            <div key={session.id} className="event-item" data-test-id={`history-session-${session.id}`}>
              <div className="event-item-header">
                <strong>
                  {new Date(session.session_start_time * 1000).toLocaleDateString()}{" "}
                  {new Date(session.session_start_time * 1000).toLocaleTimeString()}
                </strong>
                <span className="event-stage">{session.ended_reason}</span>
              </div>
              <span>
                Monitored {formatDuration(session.total_monitored_seconds)} · Focused{" "}
                {formatDuration(session.focused_time_seconds)} · Distracted{" "}
                {formatDuration(session.distracted_time_seconds)}
              </span>
              <span className="event-meta">
                Warnings {session.soft_warnings}/{session.medium_warnings}/{session.final_alerts} · Top trigger:{" "}
                {session.most_common_trigger === "none"
                  ? "none"
                  : labelContributor(session.most_common_trigger)}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
};
