import { api } from "@/lib/http";

export type ResponseRuleRead = {
  id: string;
  pack_id: string;
  trigger: string;
  response_template: string;
  locked_at: string | null;
};

export const responseRulesApi = {
  list: (packId: string) =>
    api<ResponseRuleRead[]>(`/api/v1/response-rules?pack_id=${packId}`),

  generate: (packId: string) =>
    api<ResponseRuleRead[]>(`/api/v1/response-rules/generate?pack_id=${packId}`, {
      method: "POST",
    }),

  update: (ruleId: string, response_template: string) =>
    api<ResponseRuleRead>(`/api/v1/response-rules/${ruleId}`, {
      method: "PATCH",
      body: JSON.stringify({ response_template }),
    }),

  lock: (packId: string) =>
    api<ResponseRuleRead[]>(`/api/v1/response-rules/lock?pack_id=${packId}`, {
      method: "POST",
    }),
};
