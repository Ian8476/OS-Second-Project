import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./LoginPage.module.css";
import { useAuth } from "./AuthProvider";
import { login } from "@/shared/api/auth";
import { useTranslation } from "@/shared/i18n/useTranslation";

export function LoginPage() {
  const t = useTranslation();
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@mediaintel.local");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await login(email, password);
      setSession(res.access_token, res.role);
      navigate("/cases", { replace: true });
    } catch {
      setError(t("auth.login_error"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.shell}>
      <form className={styles.card} onSubmit={onSubmit}>
        <h1 className={styles.title}>{t("auth.login_title")}</h1>
        <label className={styles.field}>
          <span>{t("auth.email")}</span>
          <input
            type="email"
            value={email}
            required
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className={styles.field}>
          <span>{t("auth.password")}</span>
          <input
            type="password"
            value={password}
            required
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className={styles.error}>{error}</p>}
        <button type="submit" className={styles.submit} disabled={loading}>
          {loading ? t("common.loading") : t("auth.login_button")}
        </button>
        <p className={styles.hint}>{t("auth.demo_hint")}</p>
      </form>
    </div>
  );
}
