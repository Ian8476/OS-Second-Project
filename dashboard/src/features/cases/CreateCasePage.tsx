import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import styles from "./CreateCasePage.module.css";
import { createCase } from "@/shared/api/cases";
import { useTranslation } from "@/shared/i18n/useTranslation";
import type { Priority } from "@/shared/api/types";

const PRIORITIES: Priority[] = ["low", "medium", "high", "critical"];

export function CreateCasePage() {
  const t = useTranslation();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>("medium");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => createCase({ title, description, priority, files }),
    onSuccess: (data) => navigate(`/cases/${data.id}`),
    onError: () => setError(t("case.create.error")),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (files.length === 0) {
      setError(t("case.create.error"));
      return;
    }
    mutation.mutate();
  }

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <h1 className={styles.title}>{t("case.create.title")}</h1>

      <label className={styles.field}>
        <span>{t("case.create.field.title")}</span>
        <input
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>

      <label className={styles.field}>
        <span>{t("case.create.field.description")}</span>
        <textarea
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>

      <label className={styles.field}>
        <span>{t("case.create.field.priority")}</span>
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as Priority)}
        >
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {t((`priority.${p}` as const))}
            </option>
          ))}
        </select>
      </label>

      <label className={styles.field}>
        <span>{t("case.create.field.files")}</span>
        <input
          type="file"
          multiple
          onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
        />
        <small className={styles.fileList}>
          {files.map((f) => f.name).join(", ")}
        </small>
      </label>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.cancel}
          onClick={() => navigate("/cases")}
        >
          {t("common.cancel")}
        </button>
        <button type="submit" className={styles.submit} disabled={mutation.isPending}>
          {mutation.isPending ? t("common.loading") : t("case.create.submit")}
        </button>
      </div>
    </form>
  );
}
