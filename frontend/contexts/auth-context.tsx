"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { auth as authApi } from "@/lib/api";
import { useProjectStore } from "@/store/useProjectStore";
import { useChatStore } from "@/app/(dashboard)/chat/_store/chat-store";

type AuthContextValue = {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  checkEmailRegistered: (email: string) => Promise<{ registered: boolean }>;
  requestLoginCode: (email: string) => Promise<void>;
  verifyLoginCode: (email: string, code: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsAuthenticated(authApi.isAuthenticated());
    setIsLoading(false);
  }, []);

  function clearStores() {
    useProjectStore.getState().reset();
    useChatStore.getState().reset();
  }

  useEffect(() => {
    if (typeof window === "undefined") return;
    const on401 = () => {
      authApi.logout();
      clearStores();
      setIsAuthenticated(false);
      router.replace("/");
    };
    window.addEventListener("auth:401", on401);
    return () => window.removeEventListener("auth:401", on401);
  }, [router]);

  const login = useCallback(async (email: string, password: string) => {
    await authApi.login(email, password);
    setIsAuthenticated(true);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    await authApi.register(email, password);
    setIsAuthenticated(true);
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    await authApi.loginWithGoogle(idToken);
    setIsAuthenticated(true);
  }, []);

  const checkEmailRegistered = useCallback(
    (email: string) => authApi.checkEmailRegistered(email),
    []
  );

  const requestLoginCode = useCallback(async (email: string) => {
    await authApi.requestLoginCode(email);
  }, []);

  const verifyLoginCode = useCallback(async (email: string, code: string) => {
    await authApi.verifyLoginCode(email, code);
    setIsAuthenticated(true);
  }, []);

  const requestPasswordReset = useCallback(async (email: string) => {
    await authApi.requestPasswordReset(email);
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    clearStores();
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        login,
        register,
        loginWithGoogle,
        checkEmailRegistered,
        requestLoginCode,
        verifyLoginCode,
        requestPasswordReset,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
