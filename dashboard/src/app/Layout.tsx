import { NavLink, Outlet } from "react-router-dom";
import styles from "./Layout.module.css";
import { useAuth } from "@/features/auth/AuthProvider";
import { useTranslation } from "@/shared/i18n/useTranslation";

export function Layout() {
  const { logout, role } = useAuth();
  const t = useTranslation();
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <h1 className={styles.brand}>{t("app.name")}</h1>
        <nav className={styles.nav}>
          <NavLink to="/cases" className={({ isActive }) => (isActive ? styles.active : styles.link)}>
            {t("nav.cases")}
          </NavLink>
          <NavLink to="/cases/new" className={({ isActive }) => (isActive ? styles.active : styles.link)}>
            {t("nav.new_case")}
          </NavLink>
          <NavLink
            to="/monitoring"
            className={({ isActive }) => (isActive ? styles.active : styles.link)}
          >
            {t("nav.monitoring")}
          </NavLink>
        </nav>
        <footer className={styles.footer}>
          <span className={styles.role}>{role ?? t("auth.role_unknown")}</span>
          <button className={styles.logout} onClick={logout}>
            {t("auth.logout")}
          </button>
        </footer>
      </aside>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
