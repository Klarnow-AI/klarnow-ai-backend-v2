import { api } from "@/lib/http";
import type { BuilderProject, BuilderProjectList } from "@/types/api-types";

const PREFIX = "/api/v1/builder/projects";

export const builder = {
  getByPack: (packId: string) =>
    api<BuilderProject>(`${PREFIX}/by-pack/${packId}`),

  get: (id: string) => api<BuilderProject>(`${PREFIX}/${id}`),

  create: (packId: string, name?: string) =>
    api<BuilderProject>(PREFIX, {
      method: "POST",
      body: JSON.stringify({ pack_id: packId, name: name || "Untitled Project" }),
    }),

  update: (
    id: string,
    data: {
      files?: Record<string, string>;
      messages?: Array<{ role: string; content: string }>;
      name?: string;
    }
  ) =>
    api<BuilderProject>(`${PREFIX}/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  publish: (id: string) =>
    api<BuilderProject>(`${PREFIX}/${id}/publish`, { method: "POST" }),

  list: () => api<BuilderProjectList>(PREFIX),

  delete: (id: string) =>
    api(`${PREFIX}/${id}`, { method: "DELETE" }),
};
