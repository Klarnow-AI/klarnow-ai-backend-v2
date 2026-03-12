import { api, fetchApiResponse, getApiErrorFromResponse } from "@/lib/http";
import type {
  DocsCompanyData,
  DocsCreateBody,
  DocsDocument,
  DocsHomeResponse,
  DocsListResponse,
  DocsTemplate,
  DocsUpdateBody,
  InvoicePublishResponse,
} from "@/types/api-types";

const docsPrefix = (packId: string) => `/api/v1/packs/${packId}/docs`;

export const docs = {
  home: (packId: string) =>
    api<DocsHomeResponse>(`${docsPrefix(packId)}/home`),

  listTemplates: (packId: string) =>
    api<DocsTemplate[]>(`${docsPrefix(packId)}/templates`),

  getCompanyData: (packId: string) =>
    api<DocsCompanyData>(`${docsPrefix(packId)}/company-data`),

  updateCompanyData: (
    packId: string,
    body: Partial<Omit<DocsCompanyData, "id" | "pack_id" | "created_at" | "updated_at">>,
  ) =>
    api<DocsCompanyData>(`${docsPrefix(packId)}/company-data`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  listDocuments: (packId: string, type?: string | null) =>
    api<DocsListResponse>(
      `${docsPrefix(packId)}/documents${type ? `?type=${encodeURIComponent(type)}` : ""}`,
    ),

  createDocument: (packId: string, body: DocsCreateBody) =>
    api<DocsDocument>(`${docsPrefix(packId)}/documents`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getDocument: (packId: string, documentId: string) =>
    api<DocsDocument>(`${docsPrefix(packId)}/documents/${encodeURIComponent(documentId)}`),

  updateDocument: (packId: string, documentId: string, body: DocsUpdateBody) =>
    api<DocsDocument>(`${docsPrefix(packId)}/documents/${encodeURIComponent(documentId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteDocument: (packId: string, documentId: string) =>
    api<void>(`${docsPrefix(packId)}/documents/${encodeURIComponent(documentId)}`, {
      method: "DELETE",
    }),

  generateDocument: (packId: string, documentId: string, notesText?: string | null) =>
    api<DocsDocument>(`${docsPrefix(packId)}/documents/${encodeURIComponent(documentId)}/generate`, {
      method: "POST",
      body: JSON.stringify(notesText ? { notes_text: notesText } : {}),
    }),

  applySectionAction: (
    packId: string,
    documentId: string,
    sectionId: string,
    action:
      | "rewrite"
      | "shorten"
      | "expand"
      | "more_formal"
      | "more_persuasive"
      | "bullets"
      | "add_next_steps"
      | "regenerate",
  ) =>
    api<DocsDocument>(
      `${docsPrefix(packId)}/documents/${encodeURIComponent(documentId)}/sections/${encodeURIComponent(sectionId)}/actions`,
      {
        method: "POST",
        body: JSON.stringify({ action }),
      },
    ),

  downloadPdf: async (packId: string, documentId: string): Promise<void> => {
    const res = await fetchApiResponse(
      `${docsPrefix(packId)}/documents/${encodeURIComponent(documentId)}/pdf`,
      {
        defaultContentType: false,
      },
    );
    if (!res.ok) {
      throw await getApiErrorFromResponse(res, "Failed to download PDF");
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `document-${documentId}.pdf`;
    a.click();
    URL.revokeObjectURL(a.href);
  },

  publishInvoice: (packId: string, documentId: string) =>
    api<InvoicePublishResponse>(`${docsPrefix(packId)}/documents/${encodeURIComponent(documentId)}/publish`, {
      method: "POST",
    }),
};
