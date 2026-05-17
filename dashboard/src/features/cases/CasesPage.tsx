import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import styles from "./CasesPage.module.css";
import { listCases } from "@/shared/api/cases";
import { StatusBadge } from "@/shared/components/StatusBadge";
import { useTranslation } from "@/shared/i18n/useTranslation";

const STATUS_OPTIONS = [
  "queued",
  "processing",
  "completed",
  "failed",
  "retrying",
  "cancelled",
] as const;

export function CasesPage() {
  const t = useTranslation();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["cases", statusFilter],
    queryFn: () => listCases({ status: statusFilter || undefined }),
    refetchInterval: 4000,
  });

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("cases.title")}</h1>
        <div className={styles.actions}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label={t("cases.filter.status")}
            className={styles.select}
          >
            <option value="">{t("cases.filter.all")}</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {t((`status.${s}` as const))}
              </option>
            ))}
          </select>
          <Link to="/cases/new" className={styles.create}>
            {t("cases.create")}
          </Link>
        </div>
      </header>

      {isLoading && <p>{t("common.loading")}</p>}
      {isError && (
        <p className={styles.error}>
          {t("common.error")}{" "}
          <button onClick={() => refetch()}>{t("common.retry")}</button>
        </p>
      )}

      {data && data.items.length === 0 && <p>{t("cases.empty")}</p>}

      {data && data.items.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>{t("cases.column.title")}</th>
              <th>{t("cases.column.status")}</th>
              <th>{t("cases.column.priority")}</th>
              <th>{t("cases.column.progress")}</th>
              <th>{t("cases.column.created")}</th>
              <th>{t("cases.column.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((c) => (
              <tr key={c.id}>
                <td>{c.title}</td>
                <td>
                  <StatusBadge status={c.status} />
                </td>
                <td>{c.priority}</td>
                <td>
                  {c.completed_subtasks} / {c.total_subtasks}
                  {c.failed_subtasks > 0 ? ` (${c.failed_subtasks} fail)` : ""}
                </td>
                <td>{new Date(c.created_at).toLocaleString()}</td>
                <td>
                  <Link to={`/cases/${c.id}`}>{t("cases.action.view")}</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
