import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

const TOKEN_KEY = "mediaintel:token";
const ROLE_KEY = "mediaintel:role";

interface AuthState {
  token: string | null;
  role: string | null;
  setSession: (token: string, role: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [role, setRole] = useState<string | null>(() => localStorage.getItem(ROLE_KEY));

  const setSession = useCallback((newToken: string, newRole: string) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(ROLE_KEY, newRole);
    setToken(newToken);
    setRole(newRole);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
    setToken(null);
    setRole(null);
    navigate("/login", { replace: true });
  }, [navigate]);

  const value = useMemo<AuthState>(
    () => ({ token, role, setSession, logout }),
    [token, role, setSession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider missing");
  return ctx;
}
