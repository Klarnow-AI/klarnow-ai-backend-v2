import { api, getToken, handleUnauthorized } from "@/lib/http";
import type { AuthAccessToken, AuthCheckEmail } from "@/types/api-types";

const AUTH_PREFIX = "/api/v1/auth";

export const auth = {
  async login(email: string, password: string) {
    const data = await api<AuthAccessToken>(`${AUTH_PREFIX}/login`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (typeof window !== "undefined")
      localStorage.setItem("klarnow_token", data.access_token);
    return data;
  },
  async register(email: string, password: string) {
    const data = await api<AuthAccessToken>(`${AUTH_PREFIX}/register`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (typeof window !== "undefined")
      localStorage.setItem("klarnow_token", data.access_token);
    return data;
  },
  async checkEmailRegistered(email: string) {
    return api<AuthCheckEmail>(`${AUTH_PREFIX}/check-email`, {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },
  async requestLoginCode(email: string) {
    await api(`${AUTH_PREFIX}/send-login-code`, {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },
  async verifyLoginCode(email: string, code: string) {
    const data = await api<AuthAccessToken>(
      `${AUTH_PREFIX}/verify-login-code`,
      {
        method: "POST",
        body: JSON.stringify({ email, code }),
      }
    );
    if (typeof window !== "undefined")
      localStorage.setItem("klarnow_token", data.access_token);
    return data;
  },
  logout() {
    if (typeof window !== "undefined") localStorage.removeItem("klarnow_token");
  },
  getToken,
  isAuthenticated(): boolean {
    return !!getToken();
  },
};
