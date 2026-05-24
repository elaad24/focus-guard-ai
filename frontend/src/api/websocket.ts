import { useEffect, useState } from "react";
import { DEFAULT_STATUS, StatusSnapshot, WS_URL } from "../types";

export type WebSocketConnectionStatus = "connecting" | "connected" | "disconnected";

export const useStatus = () => {
  const [status, setStatus] = useState<StatusSnapshot>(DEFAULT_STATUS);
  const [connectionStatus, setConnectionStatus] = useState<WebSocketConnectionStatus>("connecting");

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let isMounted = true;

    const connect = () => {
      if (!isMounted) {
        return;
      }

      setConnectionStatus("connecting");
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        if (!isMounted) {
          return;
        }
        setConnectionStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as StatusSnapshot;
          setStatus(payload);
        } catch {
          // Ignore malformed payloads.
        }
      };

      ws.onclose = () => {
        if (!isMounted) {
          return;
        }
        setConnectionStatus("disconnected");
        reconnectTimer = window.setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      ws?.close();
    };
  }, []);

  return { status, connectionStatus };
};
