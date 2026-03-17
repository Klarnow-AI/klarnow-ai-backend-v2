"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  AlertCircle,
  Check,
  Clock,
  Lock,
  Shield,
  Sparkles,
} from "@/components/icons";
import { operationsApi, type ActionLogEntryRead, type ApprovalRequestRead, type OperatingActivityRead, type OperatingProfileRead, type OperatingSummaryRead } from "@/api_requests/operations";
import { ResponseRulesEditor } from "@/components/response-rules-editor";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/page-loader";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

type ProfileFormState = {
  business_type: string;
  timezone_name: string;
  tone_guidance: string;
  business_notes: string;
  services_offers: string;
  pricing: string;
  booking_rules: string;
  contact_preferences: string;
  automation_settings: string;
  approval_settings: string;
  business_rules: string;
};

type ActivityFormState = {
  activity_type: string;
  title: string;
  summary: string;
  customer_name: string;
  customer_contact: string;
  customer_stage: string;
  suggested_reply: string;
  suggested_action: string;
  detected_reason: string;
  payload: string;
};

const ACTIVITY_OPTIONS = [
  { value: "routine_query", label: "Routine query" },
  { value: "new_lead", label: "New lead" },
  { value: "quote_request", label: "Quote request" },
  { value: "booking_request", label: "Booking request" },
  { value: "support_issue", label: "Support issue" },
  { value: "discount_request", label: "Discount request" },
  { value: "refund_request", label: "Refund request" },
  { value: "invoice_followup", label: "Invoice follow-up" },
  { value: "missed_lead_followup", label: "Missed lead follow-up" },
  { value: "custom_offer_request", label: "Custom offer request" },
  { value: "price_change_request", label: "Price change request" },
  { value: "service_scope_change", label: "Service scope change" },
  { value: "payment_term_change", label: "Payment term change" },
  { value: "manual_review", label: "Manual review" },
];

const CUSTOMER_STAGE_OPTIONS = [
  { value: "", label: "Auto-detect" },
  { value: "lead", label: "Lead" },
  { value: "booked_customer", label: "Booked customer" },
  { value: "support_query", label: "Support query" },
  { value: "existing_customer", label: "Existing customer" },
];

function prettyJson(value: Record<string, unknown> | null | undefined): string {
  if (!value || Object.keys(value).length === 0) return "";
  return JSON.stringify(value, null, 2);
}

function profileToForm(profile: OperatingProfileRead): ProfileFormState {
  return {
    business_type: profile.business_type ?? "",
    timezone_name: profile.timezone_name ?? "",
    tone_guidance: profile.tone_guidance ?? "",
    business_notes: profile.business_notes ?? "",
    services_offers: prettyJson(profile.services_offers),
    pricing: prettyJson(profile.pricing),
    booking_rules: prettyJson(profile.booking_rules),
    contact_preferences: prettyJson(profile.contact_preferences),
    automation_settings: prettyJson(profile.automation_settings),
    approval_settings: prettyJson(profile.approval_settings),
    business_rules: prettyJson(profile.business_rules),
  };
}

function emptyActivityForm(): ActivityFormState {
  return {
    activity_type: "routine_query",
    title: "",
    summary: "",
    customer_name: "",
    customer_contact: "",
    customer_stage: "",
    suggested_reply: "",
    suggested_action: "",
    detected_reason: "",
    payload: "",
  };
}

function parseJsonField(
  label: string,
  raw: string,
): Record<string, unknown> | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
    throw new Error(`${label} must be a JSON object.`);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : `Invalid ${label} JSON.`;
    throw new Error(`${label}: ${message}`);
  }
}

function formatTimestamp(value: string | null): string {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function priorityBadgeVariant(priority: string): "default" | "secondary" | "destructive" | "outline" {
  if (priority === "urgent") return "destructive";
  if (priority === "important") return "default";
  if (priority === "routine") return "secondary";
  return "outline";
}

function statusBadgeVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  if (status === "pending") return "destructive";
  if (status === "approved" || status === "resolved") return "default";
  if (status === "rejected") return "outline";
  return "secondary";
}

export default function OperationsPage() {
  const params = useParams();
  const packId = params.packId as string;
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [creatingActivity, setCreatingActivity] = useState(false);
  const [approvalBusyId, setApprovalBusyId] = useState<string | null>(null);
  const [summary, setSummary] = useState<OperatingSummaryRead | null>(null);
  const [profile, setProfile] = useState<OperatingProfileRead | null>(null);
  const [activities, setActivities] = useState<OperatingActivityRead[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequestRead[]>([]);
  const [actionLog, setActionLog] = useState<ActionLogEntryRead[]>([]);
  const [profileForm, setProfileForm] = useState<ProfileFormState | null>(null);
  const [activityForm, setActivityForm] = useState<ActivityFormState>(
    emptyActivityForm(),
  );
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadOperationsState() {
    if (!packId) return;
    setError(null);
    const [nextSummary, nextProfile, nextActivities, nextApprovals, nextActionLog] =
      await Promise.all([
        operationsApi.getSummary(packId),
        operationsApi.getProfile(packId),
        operationsApi.listActivities(packId, { limit: 25 }),
        operationsApi.listApprovals(packId, { limit: 25 }),
        operationsApi.listActionLog(packId, 25),
      ]);
    setSummary(nextSummary);
    setProfile(nextProfile);
    setProfileForm(profileToForm(nextProfile));
    setActivities(nextActivities.items);
    setApprovals(nextApprovals.items);
    setActionLog(nextActionLog.items);
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadOperationsState()
      .catch((nextError) => {
        if (!cancelled) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : "Failed to load operations workspace.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [packId]);

  async function refreshLists() {
    if (!packId) return;
    const [nextSummary, nextActivities, nextApprovals, nextActionLog] =
      await Promise.all([
        operationsApi.getSummary(packId),
        operationsApi.listActivities(packId, { limit: 25 }),
        operationsApi.listApprovals(packId, { limit: 25 }),
        operationsApi.listActionLog(packId, 25),
      ]);
    setSummary(nextSummary);
    setActivities(nextActivities.items);
    setApprovals(nextApprovals.items);
    setActionLog(nextActionLog.items);
  }

  async function handleSaveProfile(event: React.FormEvent) {
    event.preventDefault();
    if (!packId || !profileForm) return;
    setSavingProfile(true);
    setError(null);
    setNotice(null);
    try {
      const body = {
        business_type: profileForm.business_type.trim() || null,
        timezone_name: profileForm.timezone_name.trim() || null,
        tone_guidance: profileForm.tone_guidance.trim() || null,
        business_notes: profileForm.business_notes.trim() || null,
        services_offers: parseJsonField(
          "Services and offers",
          profileForm.services_offers,
        ),
        pricing: parseJsonField("Pricing", profileForm.pricing),
        booking_rules: parseJsonField("Booking rules", profileForm.booking_rules),
        contact_preferences: parseJsonField(
          "Contact preferences",
          profileForm.contact_preferences,
        ),
        automation_settings: parseJsonField(
          "Automation settings",
          profileForm.automation_settings,
        ),
        approval_settings: parseJsonField(
          "Approval settings",
          profileForm.approval_settings,
        ),
        business_rules: parseJsonField(
          "Business rules",
          profileForm.business_rules,
        ),
      };
      const updated = await operationsApi.patchProfile(packId, body);
      setProfile(updated);
      setProfileForm(profileToForm(updated));
      setNotice("Operating profile updated.");
      const nextSummary = await operationsApi.getSummary(packId);
      setSummary(nextSummary);
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Failed to save operating profile.",
      );
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleCreateActivity(event: React.FormEvent) {
    event.preventDefault();
    if (!packId) return;
    setCreatingActivity(true);
    setError(null);
    setNotice(null);
    try {
      const result = await operationsApi.createActivity(packId, {
        activity_type: activityForm.activity_type,
        title: activityForm.title.trim() || null,
        summary: activityForm.summary.trim() || null,
        customer_name: activityForm.customer_name.trim() || null,
        customer_contact: activityForm.customer_contact.trim() || null,
        customer_stage: activityForm.customer_stage || null,
        suggested_reply: activityForm.suggested_reply.trim() || null,
        suggested_action: parseJsonField(
          "Suggested action",
          activityForm.suggested_action,
        ),
        detected_reason: activityForm.detected_reason.trim() || null,
        payload: parseJsonField("Payload", activityForm.payload),
      });
      setActivityForm(emptyActivityForm());
      await refreshLists();
      setNotice(
        result.approval
          ? "Activity created and routed to approval."
          : "Activity created.",
      );
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Failed to create activity.",
      );
    } finally {
      setCreatingActivity(false);
    }
  }

  async function handleApprove(approval: ApprovalRequestRead, editBeforeApprove = false) {
    if (!packId) return;
    setApprovalBusyId(approval.id);
    setError(null);
    setNotice(null);
    try {
      let finalResponse = approval.proposed_response;
      if (editBeforeApprove) {
        const edited = window.prompt(
          "Edit the final response before approving",
          approval.proposed_response ?? "",
        );
        if (edited === null) {
          setApprovalBusyId(null);
          return;
        }
        finalResponse = edited.trim() || null;
        await operationsApi.editAndApprove(packId, approval.id, {
          final_response: finalResponse,
          final_action: approval.proposed_action,
        });
      } else {
        await operationsApi.approve(packId, approval.id, {
          final_response: finalResponse,
          final_action: approval.proposed_action,
        });
      }
      await refreshLists();
      setNotice("Approval recorded.");
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Failed to approve.",
      );
    } finally {
      setApprovalBusyId(null);
    }
  }

  async function handleReject(approval: ApprovalRequestRead) {
    if (!packId) return;
    const note = window.prompt(
      "Optional note for why this action was rejected",
      approval.decision_note ?? "",
    );
    if (note === null) return;
    setApprovalBusyId(approval.id);
    setError(null);
    setNotice(null);
    try {
      await operationsApi.reject(packId, approval.id, {
        decision_note: note.trim() || null,
      });
      await refreshLists();
      setNotice("Approval rejected.");
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Failed to reject.",
      );
    } finally {
      setApprovalBusyId(null);
    }
  }

  if (loading || !profileForm) {
    return (
      <div className="flex min-h-[60vh] w-full items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Spinner className="h-6 w-6" />
          Loading operations workspace…
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 space-y-2"
      >
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-[600] tracking-tight">Operations</h1>
          <Badge variant="outline" className="gap-1">
            <Shield className="h-3.5 w-3.5" />
            Revenue-safe control layer
          </Badge>
        </div>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Klarnow classifies activity, prepares safe next actions, and routes
          revenue-sensitive decisions for approval. Dispatch stays external.
        </p>
      </motion.div>

      {(error || notice) && (
        <div className="mb-6 space-y-3">
          {error && (
            <div className="rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}
          {notice && (
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">
              {notice}
            </div>
          )}
        </div>
      )}

      <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card asMotion delay={0.02}>
          <CardHeader className="pb-3">
            <CardDescription>Open work</CardDescription>
            <CardTitle className="text-3xl">
              {summary?.open_activities ?? 0}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-sm text-muted-foreground">
            {summary?.urgent_activities ?? 0} urgent,{" "}
            {summary?.important_activities ?? 0} important
          </CardContent>
        </Card>
        <Card asMotion delay={0.04}>
          <CardHeader className="pb-3">
            <CardDescription>Pending approvals</CardDescription>
            <CardTitle className="text-3xl">
              {summary?.pending_approvals ?? 0}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-sm text-muted-foreground">
            Revenue-sensitive actions waiting for review
          </CardContent>
        </Card>
        <Card asMotion delay={0.06}>
          <CardHeader className="pb-3">
            <CardDescription>Action log</CardDescription>
            <CardTitle className="text-3xl">
              {summary?.action_log_entries ?? 0}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-sm text-muted-foreground">
            Auditable trail of approvals and dispatch-ready actions
          </CardContent>
        </Card>
        <Card asMotion delay={0.08}>
          <CardHeader className="pb-3">
            <CardDescription>Profile readiness</CardDescription>
            <CardTitle className="text-lg">
              {summary?.profile_configured ? "Configured" : "Needs setup"}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-sm text-muted-foreground">
            Last activity {formatTimestamp(summary?.latest_activity_at ?? null)}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card asMotion delay={0.1}>
          <CardHeader>
            <CardTitle>Business memory</CardTitle>
            <CardDescription>
              Structured context Klarnow can reuse without repeated prompting.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSaveProfile}>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Business type</label>
                  <Input
                    value={profileForm.business_type}
                    onChange={(event) =>
                      setProfileForm((prev) =>
                        prev
                          ? { ...prev, business_type: event.target.value }
                          : prev,
                      )
                    }
                    placeholder="Service business, agency, salon..."
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Timezone</label>
                  <Input
                    value={profileForm.timezone_name}
                    onChange={(event) =>
                      setProfileForm((prev) =>
                        prev
                          ? { ...prev, timezone_name: event.target.value }
                          : prev,
                      )
                    }
                    placeholder="Europe/London"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Tone guidance</label>
                <Textarea
                  value={profileForm.tone_guidance}
                  onChange={(event) =>
                    setProfileForm((prev) =>
                      prev
                        ? { ...prev, tone_guidance: event.target.value }
                        : prev,
                    )
                  }
                  placeholder="Warm, direct, professional..."
                  className="min-h-[96px]"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Business notes</label>
                <Textarea
                  value={profileForm.business_notes}
                  onChange={(event) =>
                    setProfileForm((prev) =>
                      prev
                        ? { ...prev, business_notes: event.target.value }
                        : prev,
                    )
                  }
                  placeholder="Any internal notes Klarnow should keep in mind"
                  className="min-h-[110px]"
                />
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Services and offers JSON
                  </label>
                  <Textarea
                    value={profileForm.services_offers}
                    onChange={(event) =>
                      setProfileForm((prev) =>
                        prev
                          ? { ...prev, services_offers: event.target.value }
                          : prev,
                      )
                    }
                    placeholder='{"services":[{"name":"Consultation","price_from":"120"}]}'
                    className="min-h-[140px] font-mono text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Pricing JSON</label>
                  <Textarea
                    value={profileForm.pricing}
                    onChange={(event) =>
                      setProfileForm((prev) =>
                        prev ? { ...prev, pricing: event.target.value } : prev,
                      )
                    }
                    placeholder='{"currency":"GBP","packages":["Starter","Premium"]}'
                    className="min-h-[140px] font-mono text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Booking rules JSON
                  </label>
                  <Textarea
                    value={profileForm.booking_rules}
                    onChange={(event) =>
                      setProfileForm((prev) =>
                        prev
                          ? { ...prev, booking_rules: event.target.value }
                          : prev,
                      )
                    }
                    placeholder='{"deposit_required":true,"lead_time_hours":24}'
                    className="min-h-[140px] font-mono text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Contact preferences JSON
                  </label>
                  <Textarea
                    value={profileForm.contact_preferences}
                    onChange={(event) =>
                      setProfileForm((prev) =>
                        prev
                          ? {
                              ...prev,
                              contact_preferences: event.target.value,
                            }
                          : prev,
                      )
                    }
                    placeholder='{"preferred_channel":"email","response_window":"same_day"}'
                    className="min-h-[140px] font-mono text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Automation settings JSON
                  </label>
                  <Textarea
                    value={profileForm.automation_settings}
                    onChange={(event) =>
                      setProfileForm((prev) =>
                        prev
                          ? {
                              ...prev,
                              automation_settings: event.target.value,
                            }
                          : prev,
                      )
                    }
                    placeholder='{"auto_reply_routine_queries":true}'
                    className="min-h-[140px] font-mono text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Approval settings JSON
                  </label>
                  <Textarea
                    value={profileForm.approval_settings}
                    onChange={(event) =>
                      setProfileForm((prev) =>
                        prev
                          ? {
                              ...prev,
                              approval_settings: event.target.value,
                            }
                          : prev,
                      )
                    }
                    placeholder='{"always_require":["discount_request","refund_request"]}'
                    className="min-h-[140px] font-mono text-xs"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Business rules JSON</label>
                <Textarea
                  value={profileForm.business_rules}
                  onChange={(event) =>
                    setProfileForm((prev) =>
                      prev
                        ? { ...prev, business_rules: event.target.value }
                        : prev,
                    )
                  }
                  placeholder='{"priority_exceptions":[{"trigger":"vip_client","priority":"urgent"}]}'
                  className="min-h-[140px] font-mono text-xs"
                />
              </div>

              <div className="flex items-center justify-between gap-3">
                <p className="text-xs text-muted-foreground">
                  Profile record: {profile ? formatTimestamp(profile.updated_at) : "Not available"}
                </p>
                <Button type="submit" disabled={savingProfile}>
                  {savingProfile ? "Saving…" : "Save operating profile"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card asMotion delay={0.12}>
          <CardHeader>
            <CardTitle>Manual activity intake</CardTitle>
            <CardDescription>
              Create structured activities for testing approvals, priority, and
              audit logging.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleCreateActivity}>
              <div className="space-y-2">
                <label className="text-sm font-medium">Activity type</label>
                <Select
                  value={activityForm.activity_type}
                  onChange={(event) =>
                    setActivityForm((prev) => ({
                      ...prev,
                      activity_type: event.target.value,
                    }))
                  }
                >
                  {ACTIVITY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Customer stage</label>
                  <Select
                    value={activityForm.customer_stage}
                    onChange={(event) =>
                      setActivityForm((prev) => ({
                        ...prev,
                        customer_stage: event.target.value,
                      }))
                    }
                  >
                    {CUSTOMER_STAGE_OPTIONS.map((option) => (
                      <option key={option.value || "auto"} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Title</label>
                  <Input
                    value={activityForm.title}
                    onChange={(event) =>
                      setActivityForm((prev) => ({
                        ...prev,
                        title: event.target.value,
                      }))
                    }
                    placeholder="Optional title"
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Customer name</label>
                  <Input
                    value={activityForm.customer_name}
                    onChange={(event) =>
                      setActivityForm((prev) => ({
                        ...prev,
                        customer_name: event.target.value,
                      }))
                    }
                    placeholder="Jane Doe"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Customer contact
                  </label>
                  <Input
                    value={activityForm.customer_contact}
                    onChange={(event) =>
                      setActivityForm((prev) => ({
                        ...prev,
                        customer_contact: event.target.value,
                      }))
                    }
                    placeholder="jane@example.com"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Summary</label>
                <Textarea
                  value={activityForm.summary}
                  onChange={(event) =>
                    setActivityForm((prev) => ({
                      ...prev,
                      summary: event.target.value,
                    }))
                  }
                  placeholder="What happened, what was requested, and what matters?"
                  className="min-h-[110px]"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Suggested reply</label>
                <Textarea
                  value={activityForm.suggested_reply}
                  onChange={(event) =>
                    setActivityForm((prev) => ({
                      ...prev,
                      suggested_reply: event.target.value,
                    }))
                  }
                  placeholder="Draft reply or recommendation"
                  className="min-h-[110px]"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Detected reason</label>
                <Input
                  value={activityForm.detected_reason}
                  onChange={(event) =>
                    setActivityForm((prev) => ({
                      ...prev,
                      detected_reason: event.target.value,
                    }))
                  }
                  placeholder="Why Klarnow classified it this way"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Suggested action JSON
                </label>
                <Textarea
                  value={activityForm.suggested_action}
                  onChange={(event) =>
                    setActivityForm((prev) => ({
                      ...prev,
                      suggested_action: event.target.value,
                    }))
                  }
                  placeholder='{"kind":"external_followup_dispatch","recommended_next_step":"reply"}'
                  className="min-h-[110px] font-mono text-xs"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Payload JSON</label>
                <Textarea
                  value={activityForm.payload}
                  onChange={(event) =>
                    setActivityForm((prev) => ({
                      ...prev,
                      payload: event.target.value,
                    }))
                  }
                  placeholder='{"source":"manual","channel":"email"}'
                  className="min-h-[110px] font-mono text-xs"
                />
              </div>

              <Button type="submit" disabled={creatingActivity} className="w-full">
                {creatingActivity ? "Creating…" : "Create activity"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Card asMotion delay={0.14}>
          <CardHeader>
            <CardTitle>Approvals</CardTitle>
            <CardDescription>
              Commercially sensitive requests always land here first.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {approvals.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
                No pending approvals right now.
              </div>
            ) : (
              approvals.map((approval) => {
                const busy = approvalBusyId === approval.id;
                return (
                  <div
                    key={approval.id}
                    className="rounded-2xl border border-border bg-background/40 p-4"
                  >
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <Badge variant={statusBadgeVariant(approval.status)}>
                        {approval.status.replace(/_/g, " ")}
                      </Badge>
                      <Badge variant="outline">
                        {approval.category.replace(/_/g, " ")}
                      </Badge>
                    </div>
                    <p className="text-sm font-medium text-foreground">
                      {approval.reason}
                    </p>
                    {approval.proposed_response && (
                      <div className="mt-3 rounded-xl bg-muted/40 p-3">
                        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          Proposed response
                        </p>
                        <p className="whitespace-pre-wrap text-sm text-foreground/90">
                          {approval.proposed_response}
                        </p>
                      </div>
                    )}
                    {approval.proposed_action && (
                      <div className="mt-3 rounded-xl bg-muted/40 p-3">
                        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          Proposed action
                        </p>
                        <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-foreground/80">
                          {JSON.stringify(approval.proposed_action, null, 2)}
                        </pre>
                      </div>
                    )}
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        disabled={busy}
                        onClick={() => void handleApprove(approval)}
                      >
                        {busy ? "Working…" : "Approve"}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busy}
                        onClick={() => void handleApprove(approval, true)}
                      >
                        Edit & approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busy}
                        onClick={() => void handleReject(approval)}
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        <Card asMotion delay={0.16}>
          <CardHeader>
            <CardTitle>Activity inbox</CardTitle>
            <CardDescription>
              Priority-ranked operating activity with response and action modes.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {activities.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
                No activity yet. New leads and manual intake will appear here.
              </div>
            ) : (
              activities.map((activity) => (
                <div
                  key={activity.id}
                  className="rounded-2xl border border-border bg-background/40 p-4"
                >
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <Badge variant={priorityBadgeVariant(activity.priority)}>
                      {activity.priority.replace(/_/g, " ")}
                    </Badge>
                    <Badge variant="outline">
                      {activity.response_mode.replace(/_/g, " ")}
                    </Badge>
                    {activity.requires_approval && (
                      <Badge variant="destructive">approval required</Badge>
                    )}
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">
                        {activity.title || activity.activity_type.replace(/_/g, " ")}
                      </h3>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {activity.customer_name || "Unknown customer"}
                        {activity.customer_stage
                          ? ` • ${activity.customer_stage.replace(/_/g, " ")}`
                          : ""}
                        {activity.customer_contact
                          ? ` • ${activity.customer_contact}`
                          : ""}
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatTimestamp(activity.created_at)}
                    </span>
                  </div>
                  {activity.summary && (
                    <p className="mt-3 whitespace-pre-wrap text-sm text-foreground/90">
                      {activity.summary}
                    </p>
                  )}
                  {activity.detected_reason && (
                    <div className="mt-3 flex items-start gap-2 rounded-xl bg-muted/40 p-3 text-xs text-muted-foreground">
                      <Sparkles className="mt-0.5 h-4 w-4" />
                      <span>{activity.detected_reason}</span>
                    </div>
                  )}
                  {activity.suggested_action && (
                    <div className="mt-3 rounded-xl bg-muted/40 p-3">
                      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Suggested action
                      </p>
                      <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-foreground/80">
                        {JSON.stringify(activity.suggested_action, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Card asMotion delay={0.18}>
          <CardHeader>
            <CardTitle>Action log</CardTitle>
            <CardDescription>
              Audit trail for prepared dispatches, approvals, and outcomes.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {actionLog.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
                No action log entries yet.
              </div>
            ) : (
              actionLog.map((entry) => (
                <div
                  key={entry.id}
                  className="rounded-2xl border border-border bg-background/40 p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={statusBadgeVariant(entry.status)}>
                      {entry.status.replace(/_/g, " ")}
                    </Badge>
                    <Badge variant="outline">
                      {entry.execution_mode.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm font-medium text-foreground">
                    {entry.action_type.replace(/_/g, " ")}
                  </p>
                  {entry.summary && (
                    <p className="mt-1 text-sm text-foreground/85">
                      {entry.summary}
                    </p>
                  )}
                  <p className="mt-2 text-xs text-muted-foreground">
                    {formatTimestamp(entry.created_at)}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card asMotion delay={0.2}>
            <CardHeader>
              <CardTitle>Operating rules</CardTitle>
              <CardDescription>
                Existing response rules stay editable here while the broader
                operating policy layer takes shape.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="rounded-2xl border border-border bg-muted/30 p-4">
                <div className="flex items-start gap-3">
                  <Lock className="mt-0.5 h-4 w-4 text-foreground" />
                  <div>
                    Revenue-sensitive categories still require approval by
                    policy, even if a response rule exists.
                  </div>
                </div>
              </div>
              <div className="rounded-2xl border border-border bg-muted/30 p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="mt-0.5 h-4 w-4 text-foreground" />
                  <div>
                    Dispatch-ready actions are logged here, but the actual send
                    path remains an external service boundary.
                  </div>
                </div>
              </div>
              <div className="rounded-2xl border border-border bg-muted/30 p-4">
                <div className="flex items-start gap-3">
                  <Clock className="mt-0.5 h-4 w-4 text-foreground" />
                  <div>
                    New leads now publish into the operations inbox
                    automatically as important activity.
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="[&>div]:mt-0">
            <ResponseRulesEditor packId={packId} />
          </div>
        </div>
      </div>
    </div>
  );
}
