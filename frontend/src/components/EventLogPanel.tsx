import { StatusEvent } from "../types";

type EventLogPanelProps = {
  events: Array<StatusEvent>;
};

export const EventLogPanel = ({ events }: EventLogPanelProps) => {
  return (
    <section className="panel span-12" data-test-id="event-log-panel">
      <h2 className="panel-title">Event Log</h2>
      <div className="event-log">
        {events.length === 0 ? (
          <div className="event-item">No events yet.</div>
        ) : (
          events.map((event, index) => (
            <div key={`${event.timestamp}-${event.type}-${index}`} className="event-item">
              <strong>{event.type}</strong>
              <span>{event.message}</span>
              <span className="event-meta">{new Date(event.timestamp * 1000).toLocaleString()}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
};
