import { api } from "@/lib/http";

export type SubscriptionRead = {
  id: string;
  user_id: string;
  plan: string;
  credits_remaining: number;
  credits_total: number;
  status: string;
};

export const subscriptionApi = {
  get: () => api<SubscriptionRead>("/api/v1/subscription"),
  getCredits: () =>
    api<{ credits_remaining: number }>("/api/v1/subscription/credits"),
};
