import { api } from "@/lib/http";
import type {
  Lead,
  LeadListResponse,
  LeadCreateBody,
  LeadUpdateBody,
} from "@/types/api-types";

const CLIENTS_PREFIX = "/api/v1/clients";

export const clients = {
  listLeads: (packId: string, qualifiedOnly?: boolean) =>
    api<LeadListResponse>(
      `${CLIENTS_PREFIX}/leads?pack_id=${packId}${qualifiedOnly ? "&qualified_only=true" : ""}`,
    ),

  createLead: (body: LeadCreateBody) =>
    api<Lead>(`${CLIENTS_PREFIX}/leads`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getLead: (leadId: string) => api<Lead>(`${CLIENTS_PREFIX}/leads/${leadId}`),

  updateLead: (leadId: string, body: LeadUpdateBody) =>
    api<Lead>(`${CLIENTS_PREFIX}/leads/${leadId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  qualifyLead: (leadId: string) =>
    api<Lead>(`${CLIENTS_PREFIX}/leads/${leadId}/qualify`, {
      method: "POST",
    }),
};
