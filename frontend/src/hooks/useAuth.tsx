import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, onUnauthorized, tokenStore } from "../services/api";
import type { ProfileResponse } from "../types/api";

interface AuthContextValue {
  token: string | null;
  profile: ProfileResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<ProfileResponse | null>;
  setProfile: (p: ProfileResponse) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => tokenStore.get());
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(() => Boolean(tokenStore.get()));

  const logout = useCallback(() => {
    tokenStore.clear();
    setToken(null);
    setProfile(null);
  }, []);

  useEffect(() => {
    onUnauthorized(logout);
    return () => onUnauthorized(null);
  }, [logout]);

  const refreshProfile = useCallback(async () => {
    if (!tokenStore.get()) return null;
    try {
      const p = await api.getProfile();
      setProfile(p);
      return p;
    } catch {
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) void refreshProfile();
    else setLoading(false);
  }, [token, refreshProfile]);

  const authenticate = useCallback(async (fn: () => Promise<{ access_token: string }>) => {
    const res = await fn();
    tokenStore.set(res.access_token);
    setLoading(true);
    setToken(res.access_token);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      profile,
      loading,
      login: (email, password) => authenticate(() => api.login(email, password)),
      register: (email, password) => authenticate(() => api.register(email, password)),
      logout,
      refreshProfile,
      setProfile,
    }),
    [token, profile, loading, authenticate, logout, refreshProfile],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
