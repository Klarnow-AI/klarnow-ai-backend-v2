import { api } from "@/lib/http";
import type {
  GlobalImageContextItem,
  GlobalImageContextRetrieveResponse,
} from "@/types/api-types";

const API_PREFIX = "/api/v1/image-context";

export const imageContext = {
  uploadGlobal: (file: File, options?: { caption?: string; tags?: string[] }) => {
    const form = new FormData();
    form.append("file", file);
    if (options?.caption?.trim()) {
      form.append("caption", options.caption.trim());
    }
    if (options?.tags?.length) {
      form.append("tags", options.tags.join(","));
    }

    return api<GlobalImageContextItem>(`${API_PREFIX}/global/upload`, {
      method: "POST",
      body: form,
    });
  },

  retrieveGlobal: (query: string, topK = 3) =>
    api<GlobalImageContextRetrieveResponse>(`${API_PREFIX}/global/retrieve`, {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK }),
    }),
};
