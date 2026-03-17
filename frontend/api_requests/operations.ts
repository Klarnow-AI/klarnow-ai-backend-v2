import { api } from "@/lib/http";

export type OperatingProfileRead = {
  id: string;
  pack_id: string;
  business_type: string | null;
  services_offers: Record<string, unknown> | null;
  pricing: Record<string, unknown> | null;
  booking_rules: Record<string, unknown> | null;
  working_hours: Record<string, unknown> | null;
  contact_preferences: Record<string, unknown> | null;
  service_area: Record<string, unknown> | null;
  automation_settings: Record<string, unknown> | null;
  approval_settings: Record<string, unknown> | null;
  business_rules: Record<string, unknown> | null;
  tone_guidance: string | null;
  business_notes: string | null;
  timezone_name: string | null;
  created_at: string;
  updated_at: string;
};

export type OperatingProfilePatch = {
  business_type?: string | null;
  services_offers?: Record<string, unknown> | null;
  pricing?: Record<string, unknown> | null;
  booking_rules?: Record<string, unknown> | null;
  working_hours?: Record<string, unknown> | null;
  contact_preferences?: Record<string, unknown> | null;
  service_area?: Record<string, unknown> | null;
  automation_settings?: Record<string, unknown> | null;
  approval_settings?: Record<string, unknown> | null;
  business_rules?: Record<string, unknown> | null;
  tone_guidance?: string | null;
  business_notes?: string | null;
  timezone_name?: string | null;
};

export type OperatingSummaryRead = {
  profile_configured: boolean;
  open_activities: number;
  urgent_activities: number;
  important_activities: number;
  pending_approvals: number;
  action_log_entries: number;
  latest_activity_at: string | null;
};

export type OperatingActivityRead = {
  id: string;
  pack_id: string;
  source_kind: string;
  source_ref: string | null;
  activity_type: string;
  title: string | null;
  summary: string | null;
  customer_name: string | null;
  customer_contact: string | null;
  customer_stage: string | null;
  priority: string;
  commercial_sensitivity: string;
  status: string;
  response_mode: string;
  action_mode: string;
  requires_approval: boolean;
  suggested_reply: string | null;
  suggested_action: Record<string, unknown> | null;
  detected_reason: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
};

export type OperatingActivityCreate = {
  activity_type: string;
  title?: string | null;
  summary?: string | null;
  customer_name?: string | null;
  customer_contact?: string | null;
  customer_stage?: string | null;
  source_kind?: string;
  source_ref?: string | null;
  suggested_reply?: string | null;
  suggested_action?: Record<string, unknown> | null;
  detected_reason?: string | null;
  payload?: Record<string, unknown> | null;
};

export type OperatingActivityList = {
  items: OperatingActivityRead[];
  total: number;
};

export type ApprovalRequestRead = {
  id: string;
  pack_id: string;
  activity_id: string;
  category: string;
  status: string;
  reason: string;
  proposed_response: string | null;
  proposed_action: Record<string, unknown> | null;
  final_response: string | null;
  final_action: Record<string, unknown> | null;
  decision_note: string | null;
  decided_by_user_id: string | null;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ApprovalRequestList = {
  items: ApprovalRequestRead[];
  total: number;
};

export type RecommendationFeedbackRead = {
  id: string;
  pack_id: string;
  activity_id: string | null;
  approval_request_id: string | null;
  feedback_type: string;
  scenario_key: string;
  original_content: string | null;
  final_content: string | null;
  notes: string | null;
  created_by_user_id: string | null;
  created_at: string;
};

export type ApprovalDecisionResponse = {
  approval: ApprovalRequestRead;
  feedback: RecommendationFeedbackRead;
};

export type ActionLogEntryRead = {
  id: string;
  pack_id: string;
  activity_id: string | null;
  approval_request_id: string | null;
  action_type: string;
  execution_mode: string;
  status: string;
  summary: string | null;
  provider_name: string | null;
  provider_ref: string | null;
  payload: Record<string, unknown> | null;
  created_by_user_id: string | null;
  created_at: string;
};

export type ActionLogEntryList = {
  items: ActionLogEntryRead[];
  total: number;
};

export type ActivityCreateResponse = {
  activity: OperatingActivityRead;
  approval: ApprovalRequestRead | null;
};

const prefix = (packId: string) => `/api/v1/packs/${packId}/operations`;

export const operationsApi = {
  getProfile: (packId: string) =>
    api<OperatingProfileRead>(`${prefix(packId)}/profile`),

  patchProfile: (packId: string, body: OperatingProfilePatch) =>
    api<OperatingProfileRead>(`${prefix(packId)}/profile`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  getSummary: (packId: string) =>
    api<OperatingSummaryRead>(`${prefix(packId)}/summary`),

  listActivities: (
    packId: string,
    params?: { status?: string; priority?: string; limit?: number },
  ) => {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.priority) search.set("priority", params.priority);
    if (params?.limit != null) search.set("limit", String(params.limit));
    const query = search.toString();
    return api<OperatingActivityList>(
      `${prefix(packId)}/activities${query ? `?${query}` : ""}`,
    );
  },

  createActivity: (packId: string, body: OperatingActivityCreate) =>
    api<ActivityCreateResponse>(`${prefix(packId)}/activities`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listApprovals: (
    packId: string,
    params?: { status?: string; limit?: number },
  ) => {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.limit != null) search.set("limit", String(params.limit));
    const query = search.toString();
    return api<ApprovalRequestList>(
      `${prefix(packId)}/approvals${query ? `?${query}` : ""}`,
    );
  },

  approve: (
    packId: string,
    approvalId: string,
    body: {
      final_response?: string | null;
      final_action?: Record<string, unknown> | null;
      decision_note?: string | null;
    },
  ) =>
    api<ApprovalDecisionResponse>(
      `${prefix(packId)}/approvals/${approvalId}/approve`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),

  editAndApprove: (
    packId: string,
    approvalId: string,
    body: {
      final_response?: string | null;
      final_action?: Record<string, unknown> | null;
      decision_note?: string | null;
    },
  ) =>
    api<ApprovalDecisionResponse>(
      `${prefix(packId)}/approvals/${approvalId}/edit-and-approve`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),

  reject: (
    packId: string,
    approvalId: string,
    body: { decision_note?: string | null },
  ) =>
    api<ApprovalDecisionResponse>(
      `${prefix(packId)}/approvals/${approvalId}/reject`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),

  listActionLog: (packId: string, limit = 50) =>
    api<ActionLogEntryList>(`${prefix(packId)}/action-log?limit=${limit}`),
};
