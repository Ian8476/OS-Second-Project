import { useEffect, useRef, useState } from "react";

export interface WsMessage {
  type: string;
  case_id?: string;
  payload?: Record<string, unknown>;
  occurred_at?: string;
  scope?: string;
}

export function useWebSocket(url: string | null) {
  const [messages, setMessages] = useState<WsMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!url) return;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (ev) => {
      try {
        const parsed: WsMessage = JSON.parse(ev.data);
        setMessages((prev) => [parsed, ...prev].slice(0, 200));
      } catch {
        // ignorar mensajes que no sean JSON valido
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [url]);

  return { messages, connected };
}
