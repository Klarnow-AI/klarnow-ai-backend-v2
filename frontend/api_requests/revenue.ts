import { api } from "@/lib/http";
import { getApiErrorMessage, getHeaders, getReadableFetchError } from "@/lib/http";
import { API_BASE } from "@/lib/utils";
import type {
  Invoice,
  InvoiceCreateBody,
  InvoiceUpdateBody,
  InvoiceListResponse,
  ConnectStatusResponse,
  ConnectOnboardingLinkResponse,
  InvoicePublishResponse,
  Proposal,
  ProposalCreateBody,
  ProposalUpdateBody,
  ProposalListResponse,
  ProposalGenerateResponse,
} from "@/types/api-types";

const REVENUE_PREFIX = "/api/v1/revenue";

export const revenue = {
  listProposals: (packId: string) =>
    api<ProposalListResponse>(
      `${REVENUE_PREFIX}/packs/${packId}/proposals`
    ),

  createProposal: (packId: string, body: ProposalCreateBody) =>
    api<Proposal>(`${REVENUE_PREFIX}/packs/${packId}/proposals`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateProposal: (proposalId: string, body: ProposalUpdateBody) =>
    api<Proposal>(`${REVENUE_PREFIX}/proposals/${proposalId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  generateProposalDraft: (packId: string, clientId?: string | null) =>
    api<ProposalGenerateResponse>(
      `${REVENUE_PREFIX}/packs/${packId}/proposals/generate`,
      {
        method: "POST",
        body: JSON.stringify({ client_id: clientId ?? null }),
      }
    ),

  getProposalPdfUrl: (proposalId: string) =>
    `${REVENUE_PREFIX}/proposals/${proposalId}/pdf`,

  /** Fetch proposal PDF with auth and trigger browser download. */
  downloadProposalPdf: async (proposalId: string): Promise<void> => {
    const url = `${API_BASE}${REVENUE_PREFIX}/proposals/${proposalId}/pdf`;
    let res: Response;
    try {
      res = await fetch(url, { headers: getHeaders() });
    } catch (error) {
      throw new Error(
        getReadableFetchError(
          error,
          "Proposal download request could not reach the server. Check that the backend is running and try again.",
        ),
      );
    }
    if (!res.ok) {
      const err = await res
        .json()
        .catch(() => ({ message: res.statusText, request_id: res.headers.get("x-request-id") }));
      throw new Error(getApiErrorMessage(err, "Failed to download PDF"));
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `proposal-${proposalId}.pdf`;
    a.click();
    URL.revokeObjectURL(a.href);
  },

  listInvoices: (packId: string) =>
    api<InvoiceListResponse>(`${REVENUE_PREFIX}/packs/${packId}/invoices`),

  createInvoice: (packId: string, body: InvoiceCreateBody) =>
    api<Invoice>(`${REVENUE_PREFIX}/packs/${packId}/invoices`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateInvoice: (invoiceId: string, body: InvoiceUpdateBody) =>
    api<Invoice>(`${REVENUE_PREFIX}/invoices/${invoiceId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  remindOverdue: () =>
    api<{ overdue_count: number; reminders_sent: number }>(
      `${REVENUE_PREFIX}/invoices/remind-overdue`,
      { method: "POST" }
    ),

  getConnectStatus: () =>
    api<ConnectStatusResponse>(`${REVENUE_PREFIX}/connect/status`),

  createConnectOnboardingLink: () =>
    api<ConnectOnboardingLinkResponse>(`${REVENUE_PREFIX}/connect/onboarding-link`, {
      method: "POST",
    }),

  publishInvoice: (invoiceId: string) =>
    api<InvoicePublishResponse>(`${REVENUE_PREFIX}/invoices/${invoiceId}/publish`, {
      method: "POST",
    }),
};
