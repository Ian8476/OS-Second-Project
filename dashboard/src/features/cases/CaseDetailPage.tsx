import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import styles from "./CaseDetailPage.module.css";
import { cancelCase, getCase, getReportPresignedUrl } from "@/shared/api/cases";
import { useTranslation } from "@/shared/i18n/useTranslation";
import { StatusBadge } from "@/shared/components/StatusBadge";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { useAuth } from "@/features/auth/AuthProvider";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);
const WS_BASE = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000/ws";

export function CaseDetailPage() {
  const t = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["case", id],
    queryFn: () => getCase(id!),
    enabled: !!id,
    refetchInterval: 5000,
  });

  const wsUrl = useMemo(() => {
    if (!id || !token) return null;
    return `${WS_BASE}/cases/${id}?token=${encodeURIComponent(token)}`;
  }, [id, token]);

  const { messages, connected } = useWebSocket(wsUrl);

  const cancelMut = useMutation({
    mutationFn: () => cancelCase(id!, reason || undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["case", id] }),
  });

  async function onDownload() {
    if (!id) return;
    const url = await getReportPresignedUrl(id);
    window.open(url, "_blank", "noopener");
  }

  if (isLoading || !data) return <p>{t("common.loading")}</p>;

  const progressPct = data.total_subtasks
    ? Math.round((data.completed_subtasks / data.total_subtasks) * 100)
    : 0;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>{data.title}</h1>
          <p className={styles.muted}>{data.description || ""}</p>
          <StatusBadge status={data.status} />
        </div>
        <div className={styles.actions}>
          {data.report_storage_key ? (
            <button onClick={onDownload} className={styles.primary}>
              {t("case.detail.download_report")}
            </button>
          ) : (
            <span className={styles.muted}>{t("case.detail.report_not_ready")}</span>
          )}
        </div>
      </header>

      <section className={styles.progress}>
        <div className={styles.barOuter}>
          <div className={styles.barInner} style={{ width: `${progressPct}%` }} />
        </div>
        <span className={styles.progressLabel}>
          {data.completed_subtasks} / {data.total_subtasks} ({progressPct}%)
        </span>
      </section>

      <section className={styles.grid}>
        <article className={styles.card}>
          <h2>{t("case.detail.sources")}</h2>
          <ul>
            {data.data_sources.map((ds) => (
              <li key={ds.id}>
                <strong>{ds.type}</strong> — {ds.original_filename ?? ds.storage_key}
              </li>
            ))}
          </ul>
        </article>

        <article className={styles.card}>
          <h2>{t("case.detail.subtasks")}</h2>
          <table className={styles.subtable}>
            <thead>
              <tr>
                <th>Worker</th>
                <th>Estado</th>
                <th>Intentos</th>
              </tr>
            </thead>
            <tbody>
              {data.subtasks.map((st) => (
                <tr key={st.id}>
                  <td>{st.worker_type}</td>
                  <td>
                    <StatusBadge status={st.status} />
                  </td>
                  <td>{st.attempts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className={styles.card}>
          <h2>{t("case.detail.findings")}</h2>
          {data.findings.length === 0 ? (
            <p className={styles.muted}>—</p>
          ) : (
            <ul className={styles.findings}>
              {data.findings.map((f) => (
                <li key={f.id} data-severity={f.severity}>
                  <header>
                    <strong>{f.category}</strong>{" "}
                    <span className={styles.muted}>sev {f.severity}</span>
                  </header>
                  <pre>{JSON.stringify(f.evidence, null, 2)}</pre>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className={styles.card}>
          <h2>
            {t("case.detail.live_log")}{" "}
            <small className={styles.muted}>
              {connected ? "online" : "offline"}
            </small>
          </h2>
          <ul className={styles.events}>
            {messages.map((m, i) => (
              <li key={i}>
                <code>{m.type}</code>
                {m.occurred_at && (
                  <span className={styles.muted}> · {m.occurred_at}</span>
                )}
                {m.payload && (
                  <pre>{JSON.stringify(m.payload, null, 2)}</pre>
                )}
              </li>
            ))}
          </ul>
        </article>
      </section>

      {!TERMINAL.has(data.status) && (
        <section className={styles.cancel}>
          <h3>{t("case.detail.cancel_button")}</h3>
          <input
            placeholder={t("case.detail.cancel_reason")}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <button
            className={styles.danger}
            onClick={() => cancelMut.mutate()}
            disabled={cancelMut.isPending}
          >
            {t("case.detail.cancel_button")}
          </button>
        </section>
      )}
    </div>
  );
}
