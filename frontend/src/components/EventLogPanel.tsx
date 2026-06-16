import { StatusEvent } from "../types";
import { labelContributor, warningStageLabels } from "../lib/contributorLabels";

type EventLogPanelProps = {
  events: Array<StatusEvent>;
};

const stageClassName = (stage: string | undefined): string => {
  if (!stage) {
    return "event-stage";
  }
  return `event-stage event-stage-${stage}`;
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
            <div
              key={`${event.timestamp}-${event.type}-${index}`}
              className="event-item"
              data-test-id={`event-item-${event.type}`}
            >
              <div className="event-item-header">
                <strong>{event.type}</strong>
                {event.warning_stage ? (
                  <span
                    className={stageClassName(event.warning_stage)}
                    data-test-id="event-warning-stage"
                  >
                    {warningStageLabels[event.warning_stage] ?? event.warning_stage}
                  </span>
                ) : null}
              </div>
              <span>{event.message}</span>
              {event.contributors && event.contributors.length > 0 ? (
                <div className="event-reasons" data-test-id="event-reasons">
                  {event.contributors.map((key) => (
                    <span key={key} className="event-reason-chip" data-test-id={`event-reason-${key}`}>
                      {labelContributor(key)}
                    </span>
                  ))}
                </div>
              ) : null}
              <span className="event-meta">{new Date(event.timestamp * 1000).toLocaleString()}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
};
