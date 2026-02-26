import { api } from "@/lib/http";

export type FollowUpTaskRead = {
  id: string;
  pack_id: string;
  lead_id: string | null;
  task_type: string;
  due_date: string;
  status: string;
  message_template: string;
  template_key?: string | null;
  channel?: string | null;
  lead_name?: string | null;
  last_interaction_summary?: string | null;
  created_at: string;
  completed_at: string | null;
};

export const tasksApi = {
  getPending: (packId: string) =>
    api<FollowUpTaskRead[]>(`/api/v1/tasks?pack_id=${packId}&status=pending`),

  complete: (taskId: string) =>
    api<FollowUpTaskRead>(`/api/v1/tasks/${taskId}/complete`, { method: "POST" }),

  skip: (taskId: string) =>
    api<FollowUpTaskRead>(`/api/v1/tasks/${taskId}/skip`, { method: "POST" }),
};
