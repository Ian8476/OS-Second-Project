import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import styles from "./MonitoringPage.module.css";
import { listCases } from "@/shared/api/cases";
import { useTranslation } from "@/shared/i18n/useTranslation";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { useAuth } from "@/features/auth/AuthProvider";
import { StatusBadge } from "@/shared/components/StatusBadge";

const WS_BASE = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000/ws";

const STATUSES = ["queued", "processing", "completed", "failed", "retrying", "cancelled"];

export function MonitoringPage() {
  const t = useTranslation();
  const { token } = useAuth();

  const { data } = useQuery({
    queryKey: ["cases-all"],
    queryFn: () => listCases({ pageSize: 100 }),
    refetchInterval: 5000,
  });

  const byStatus = useMemo(() => {
    const result: Record<string, number> = {};
    for (const s of STATUSES) result[s] = 0;
    for (const c of data?.items ?? []) {
      result[c.status] = (result[c.status] ?? 0) + 1;
    }
    return result;
  }, [data]);

  const wsUrl = token ? `${WS_BASE}/monitoring?token=${encodeURIComponent(token)}` : null;
  const { messages, connected } = useWebSocket(wsUrl);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>{t("monitoring.title")}</h1>
        <div className={styles.links}>
          <a href="http://localhost:5555" target="_blank" rel="noreferrer">
            {t("monitoring.flower_link")}
          </a>
          <a href="http://localhost:3000" target="_blank" rel="noreferrer">
            {t("monitoring.grafana_link")}
          </a>
          <a href="http://localhost:15672" target="_blank" rel="noreferrer">
            {t("monitoring.rabbitmq_link")}
          </a>
        </div>
      </header>

      <section className={styles.cards}>
        {STATUSES.map((s) => (
          <div key={s} className={styles.card}>
            <span className={styles.metric}>{byStatus[s]}</span>
            <StatusBadge status={s} />
          </div>
        ))}
      </section>

      <section className={styles.events}>
        <h2>
          {t("monitoring.events")}{" "}
          <small>{connected ? "online" : "offline"}</small>
        </h2>
        <ul>
          {messages.map((m, i) => (
            <li key={i}>
              <code>{m.type}</code> {m.case_id && <span>· {m.case_id}</span>}
              {m.payload && <pre>{JSON.stringify(m.payload, null, 2)}</pre>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
