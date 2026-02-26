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
  async requestPasswordReset(email: string) {
    await api(`${AUTH_PREFIX}/forgot-password`, {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },
  async resetPassword(token: string, newPassword: string) {
    await api(`${AUTH_PREFIX}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  },
  logout() {
    if (typeof window !== "undefined") localStorage.removeItem("klarnow_token");
  },
  async deleteAccount() {
    await api(`${AUTH_PREFIX}/account`, { method: "DELETE" });
    if (typeof window !== "undefined") localStorage.removeItem("klarnow_token");
  },
  async changePassword(currentPassword: string, newPassword: string) {
    await api(`${AUTH_PREFIX}/change-password`, {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
  },
  getToken,
  isAuthenticated(): boolean {
    return !!getToken();
  },
};
