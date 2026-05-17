import styles from "./StatusBadge.module.css";
import { useTranslation } from "@/shared/i18n/useTranslation";
import type { StringKey } from "@/shared/i18n/strings";
import clsx from "clsx";

const STATUS_VARIANT: Record<string, string> = {
  queued: styles.queued,
  processing: styles.processing,
  completed: styles.completed,
  failed: styles.failed,
  retrying: styles.retrying,
  cancelled: styles.cancelled,
  pending: styles.queued,
};

interface Props {
  status: string;
}

export function StatusBadge({ status }: Props) {
  const t = useTranslation();
  const cls = STATUS_VARIANT[status] ?? styles.queued;
  const key = (`status.${status}` as StringKey);
  return <span className={clsx(styles.badge, cls)}>{t(key)}</span>;
}
