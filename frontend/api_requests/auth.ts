import { api, clearToken, getToken, refreshAccessToken, setToken } from "@/lib/http";
import type { AuthAccessToken, AuthCheckEmail } from "@/types/api-types";

const AUTH_PREFIX = "/api/v1/auth";

function storeAccessToken(data: AuthAccessToken): AuthAccessToken {
  setToken(data.access_token);
  return data;
}

export const auth = {
  async login(email: string, password: string) {
    return storeAccessToken(
      await api<AuthAccessToken>(`${AUTH_PREFIX}/login`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
        retryOnAuthError: false,
      })
    );
  },
  async register(email: string, password: string) {
    return storeAccessToken(
      await api<AuthAccessToken>(`${AUTH_PREFIX}/register`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
        retryOnAuthError: false,
      })
    );
  },
  async loginWithGoogle(idToken: string) {
    return storeAccessToken(
      await api<AuthAccessToken>(`${AUTH_PREFIX}/google`, {
        method: "POST",
        body: JSON.stringify({ id_token: idToken }),
        retryOnAuthError: false,
      })
    );
  },
  async checkEmailRegistered(email: string) {
    return api<AuthCheckEmail>(`${AUTH_PREFIX}/check-email`, {
      method: "POST",
      body: JSON.stringify({ email }),
      retryOnAuthError: false,
    });
  },
  async requestLoginCode(email: string) {
    await api(`${AUTH_PREFIX}/send-login-code`, {
      method: "POST",
      body: JSON.stringify({ email }),
      retryOnAuthError: false,
    });
  },
  async verifyLoginCode(email: string, code: string) {
    return storeAccessToken(
      await api<AuthAccessToken>(`${AUTH_PREFIX}/verify-login-code`, {
        method: "POST",
        body: JSON.stringify({ email, code }),
        retryOnAuthError: false,
      })
    );
  },
  async requestPasswordReset(email: string) {
    await api(`${AUTH_PREFIX}/forgot-password`, {
      method: "POST",
      body: JSON.stringify({ email }),
      retryOnAuthError: false,
    });
  },
  async resetPassword(token: string, newPassword: string) {
    await api(`${AUTH_PREFIX}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
      retryOnAuthError: false,
    });
  },
  async restoreSession(): Promise<boolean> {
    if (getToken()) return true;
    return !!(await refreshAccessToken());
  },
  async logout() {
    try {
      await api(`${AUTH_PREFIX}/logout`, {
        method: "POST",
        retryOnAuthError: false,
      });
    } finally {
      clearToken();
    }
  },
  clearLocalAuth() {
    clearToken();
  },
  async deleteAccount() {
    try {
      await api(`${AUTH_PREFIX}/account`, { method: "DELETE" });
    } finally {
      clearToken();
    }
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
