/** API payload and response contracts. */

export type AuthAccessToken = {
  access_token: string;
};

export type AuthCheckEmail = {
  registered: boolean;
};

export type LandingPack = {
  id: string;
  name: string;
};

export type LandingContext = {
  pack: LandingPack | null;
  stage: "no_pack" | "brand_os_done" | "page_live" | "sprint" | "leads";
  sprintDay: number | null;
  leadCount: number | null;
};

export type NextActionChip = {
  label: string;
  href: string | null;
};

export type NextAction = {
  actionText: string;
  actionChips: NextActionChip[];
  stage: string;
  canProceed: boolean;
  blockerMessage: string | null;
  whyItMatters?: string | null;
  timeEstimate?: string | null;
  progressCounters?: Record<string, string> | null;
};

/** MVP landing complete: 3 questions + pack name → Pack + Sprint created */
export type LandingCompleteBody = {
  pack_name: string;
  what_do_you_sell: string;
  who_is_it_for: string;
  where_are_you_based: string;
};

export type LandingCompleteResponse = {
  pack_id: string;
  redirect: string;
};

/** 14-day Sprint (MVP) */
export type DayCardRead = {
  id: string;
  sprint_id: string;
  day_number: number;
  ai_output: Record<string, unknown> | null;
  user_action: string | null;
  definition_of_done: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SprintRead = {
  id: string;
  pack_id: string;
  status: string;
  mode: string;
  current_day: number;
  started_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  day_cards: DayCardRead[];
};

export type SprintDayDetail = {
  day_number: number;
  title: string;
  ai_output: Record<string, unknown> | null;
  user_action: string | null;
  definition_of_done: string | null;
  completed_at: string | null;
  unlocked: boolean;
  blocker_message?: string | null;
  completion_blocked_message?: string | null;
};

export type TodayTaskItem = {
  id: string;
  label: string;
  checked: boolean;
};

export type SprintTodayTasksRead = {
  has_sprint: boolean;
  sprint_id: string | null;
  day_number: number | null;
  day_title: string | null;
  overview: string | null;
  time_estimate: string | null;
  source: string | null;
  can_execute: boolean;
  tasks: TodayTaskItem[];
};

export type TodayTaskToggleBody = {
  day_number: number;
  task_id: string;
  checked: boolean;
};

export type Pack = {
  id: string;
  name: string;
  status: string;
  pack_type?: string;
  /** Whether the pack's campaign is active (list responses only). null = no campaign. */
  campaign_is_active?: boolean | null;
  onboarding_answers?: Record<string, string>;
  onboarding_completed_at?: string | null;
  /** Set when async onboarding (brand/orchestrator) has finished; poll GET pack until this is set after 202 from complete. */
  onboarding_background_completed_at?: string | null;
  core_concept?: string | null;
  created_at: string;
  updated_at: string;
  created_by_user_id: string;
  client_id?: string | null;
  brand_name?: string | null;
  primary_cta?: string | null;
  usp_category?: string | null;
  usp_statement?: string | null;
  usp_proof?: string | null;
  usp_locked_line?: string | null;
  proof_types?: string[] | null;
  proof_text?: string | null;
  day_0_completed_at?: string | null;
  offer_one_liner?: string | null;
  primary_pain?: string | null;
  primary_outcome?: string | null;
  hero_angle?: string | null;
};

/** Response from POST .../onboarding/complete (200) */
export type OnboardingCompleteResponse = {
  pack: Pack;
  is_existing_brand: boolean;
};

/** Response from POST .../onboarding/complete (202). Poll GET pack until onboarding_background_completed_at is set. */
export type OnboardingCompleteAccepted = {
  status: "processing";
  pack_id: string;
  job_id?: string | null;
};

/** Response from GET .../onboarding/status. */
export type OnboardingJobStatus = {
  status: "not_started" | "queued" | "running" | "completed" | "failed";
  job_id?: string | null;
  attempt: number;
  max_attempts: number;
  queued_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  last_error?: string | null;
};

/** Brand OS domain types (match backend domain_schema). */
export type BrandFoundation = {
  brand_name: string;
  main_audience: string[];
  one_line_offer: string;
  brand_purpose: string[];
  vision_12_month: string[];
  brand_industry: string;
};

export type MissionVision = {
  mission: string;
  vision: string;
  promise: string;
};

export type AudiencePersona = {
  persona: string;
  needs: string[];
  pain_points: string[];
};

export type PositioningDifferentiation = {
  statement: string;
  unique_advantage: string;
};

export type VoicePersonality = {
  profile: string[];
  archetype: string;
  we_are: string[];
  we_are_not: string[];
};

export type CoreMessagingHierarchy = {
  elevator_pitch: string;
  proof_points: string[];
};

export type StyleDirectionSeeds = {
  typography: string;
  design_cues: string[];
  palette: string[];
};

export type BrandStrategyProfile = {
  mission_vision: MissionVision;
  audience_personas: AudiencePersona[];
  positioning_differentiation: PositioningDifferentiation;
  voice_personality: VoicePersonality;
  core_messaging_hierarchy: CoreMessagingHierarchy;
  style_direction_seeds: StyleDirectionSeeds;
};

/** Brand OS (versioned strategy per pack). */
export type BrandOS = {
  id: string;
  pack_id: string;
  version: string;
  foundation: BrandFoundation;
  brand_strategy: BrandStrategyProfile;
  is_active: boolean;
  created_at: string;
};

export type PackListResponse = {
  items: Pack[];
  total: number;
};

/** Pack overview summary (Brand OS → Proof Vault). */
export type BrandOSSummary = {
  mission: string | null;
  vision: string | null;
  has_positioning: boolean;
};

export type CampaignSummary = {
  primary_cta: string | null;
  goal_summary: string | null;
};

export type WebsiteSummary = {
  live_url: string | null;
  published_at: string | null;
};

export type PlanTrackerSummary = {
  horizon: string | null;
  sprint_day: number | null;
  has_sprint: boolean;
};

export type LeadsSummary = {
  total: number;
  qualified: number;
};

export type ProposalsSummary = {
  total: number;
  sent: number;
  accepted: number;
  declined: number;
};

export type InvoicesSummary = {
  total: number;
  sent: number;
  paid: number;
  overdue: number;
};

/** Proposal (revenue). API: /api/v1/revenue */
export type ProposalStatus = "draft" | "sent" | "accepted" | "declined";

/** Kanban columns: one per status (Option B). */
export const PROPOSAL_KANBAN_STAGES: ProposalStatus[] = [
  "draft",
  "sent",
  "accepted",
  "declined",
];

export type Proposal = {
  id: string;
  pack_id: string;
  client_id: string | null;
  /** When listing proposals, API may include resolved client/lead name. */
  client_name?: string | null;
  status: string;
  amount: string;
  currency: string;
  due_date: string | null;
  content: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type ProposalCreateBody = {
  amount: string;
  currency?: string;
  due_date?: string | null;
  content?: Record<string, unknown> | null;
  client_id?: string | null;
};

export type ProposalUpdateBody = {
  status?: string;
  amount?: string;
  currency?: string;
  due_date?: string | null;
  content?: Record<string, unknown> | null;
};

export type ProposalListResponse = {
  items: Proposal[];
  total: number;
};

/** Generated proposal draft from POST .../proposals/generate */
export type ProposalLineItem = {
  label: string;
  amount: string | null;
  description: string;
};

export type ProposalGeneratedContent = {
  description?: string;
  line_items?: ProposalLineItem[];
  terms?: string;
  notes?: string;
};

export type ReferenceSnippet = {
  chunk_id: string;
  score: number;
  excerpt: string;
};

export type ProposalGenerateResponse = {
  content: ProposalGeneratedContent;
  suggested_amount: string | null;
  suggested_due_date: string | null;
  references?: ReferenceSnippet[] | null;
};

/** Invoice (revenue). API: /api/v1/revenue */
export type Invoice = {
  id: string;
  pack_id: string;
  client_id: string | null;
  client_name?: string | null;
  client_email?: string | null;
  status: string;
  amount: string;
  currency: string;
  due_date: string | null;
  content: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  stripe_invoice_id?: string | null;
  stripe_hosted_url?: string | null;
};

export type InvoiceCreateBody = {
  amount: string;
  currency?: string;
  due_date?: string | null;
  content?: Record<string, unknown> | null;
  client_id?: string | null;
};

export type InvoiceUpdateBody = {
  status?: string;
  amount?: string;
  currency?: string;
  due_date?: string | null;
  content?: Record<string, unknown> | null;
};

export type InvoiceListResponse = {
  items: Invoice[];
  total: number;
};

export type ConnectStatusResponse = {
  connected: boolean;
  onboarding_complete: boolean;
};

export type ConnectOnboardingLinkResponse = {
  url: string;
};

export type InvoicePublishResponse = {
  payment_link: string;
  stripe_invoice_id: string;
};

export type PackSummaryResponse = {
  pack: Pack;
  brand_os: BrandOSSummary | null;
  campaign: CampaignSummary | null;
  website: WebsiteSummary | null;
  plan_tracker: PlanTrackerSummary | null;
  leads: LeadsSummary;
  proposals: ProposalsSummary;
  invoices: InvoicesSummary;
  proofs_count: number;
  assets_count: number;
};

export type Conversation = {
  id: string;
  user_id: string;
  pack_id: string | null;
  day_context?: number | null;
  created_at: string;
  updated_at: string;
  /** First message content (truncated), when returned by list endpoint. */
  title?: string | null;
};

export type DayQuestionContext = {
  field_key: string;
  input_placeholder?: string;
  input_type?: "input" | "textarea" | "choice";
  suggestion_chips: { label: string; value: string }[];
  show_resuggest: boolean;
};

export type MessageAttachment = {
  id: string;
  file_name: string;
  content_type: string | null;
  size_bytes: number;
  has_text_content: boolean;
};

export type ChatAttachment = MessageAttachment & {
  conversation_id: string;
  created_at: string;
};

export type Message = {
  id: string;
  conversation_id: string;
  role: string;
  content: string | null;
  tool_calls: unknown;
  tool_results: unknown;
  attachments?: MessageAttachment[] | null;
  is_preview: boolean;
  created_at: string;
};

export type ConversationListResponse = {
  items: Conversation[];
  total: number;
};

export type MessageListResponse = {
  items: Message[];
  total: number;
};

export type SuggestedPromptsResponse = {
  prompts: string[];
};

/** Creative assets (poster, flyer, video). */
export type CreativeAssetChatMessage = {
  role: "user" | "assistant";
  content: string;
  meta?: {
    kind?: "background_generation";
    label?: string;
    taskLabel?: string;
    mode?: string;
    modeLabel?: string;
  };
};

export type CreativeAsset = {
  id: string;
  pack_id: string;
  type: string;
  version: string | null;
  name: string | null;
  template_id: string | null;
  source_code: string | null;
  output_key: string | null;
  script: string | null;
  srt_key: string | null;
  sprint_day: number | null;
  chat_messages: CreativeAssetChatMessage[] | null;
  created_at: string;
};

export type CreativeAssetListResponse = {
  items: CreativeAsset[];
  total: number;
};

export type CreativeAssetCreateBody = {
  pack_id: string;
  type: "poster" | "flyer";
  name: string;
  source_code: string;
  template_id?: string | null;
  chat_messages?: CreativeAssetChatMessage[] | null;
};

/** Onboarding: extract brand (Path A – existing brand). */
export type ExtractBrandBody = {
  input_type: "url" | "paste" | "logo";
  url?: string | null;
  pasted_text?: string | null;
  logo_file_key?: string | null;
};

export type ExtractBrandResponse = {
  brand_name: string;
  offer_cues: string[];
  tagline?: string | null;
  description?: string | null;
  industry?: string | null;
  contact_info?: {
    email?: string | null;
    phone?: string | null;
    address?: string | null;
  };
  social_links?: string[];
  logo_url?: string | null;
  color_candidates?: string[];
  raw_extract?: Record<string, unknown> | null;
};

/** Onboarding: generate starter brand (Path B – new brand). */
export type GenerateStarterBrandBody = {
  brand_name: string;
  vibe_chips: string[];
};

export type GenerateStarterBrandResponse = {
  wordmark_svg_or_url: string;
  palette: {
    primary?: string;
    secondary?: string;
    accent?: string;
    [key: string]: string | undefined;
  };
};

export type GenerateLogoBody = {
  brand_name: string;
  prompt?: string | null; // style description
  color_scheme?: string | null; // e.g. "blue and white"
  color_palette?: {
    primary?: string;
    secondary?: string;
    accent?: string;
    [key: string]: string | undefined;
  } | null; // brand colors for logo
  brand_os_summary?: string | null; // Brand OS context for generation
};

export type GenerateLogoResponse = {
  logo_url: string;
  wordmark_svg_or_url?: string | null;
};

export type UploadLogoResponse = {
  logo_url: string;
};

/** Pipeline stages for Kanban columns */
export const PIPELINE_STAGES = [
  "contacted",
  "drafting",
  "proposal",
  "closed",
] as const;
export type PipelineStage = (typeof PIPELINE_STAGES)[number];

/** Leads (pack-scoped). API: /api/v1/clients/leads */
export type Lead = {
  id: string;
  pack_id: string;
  name: string;
  phone: string | null;
  email: string | null;
  source: string | null;
  status: string;
  summary: string | null;
  budget_range: string | null;
  urgency: string | null;
  client_id: string | null;
  pipeline_stage: string;
  due_date: string | null;
  deal_value: number | null;
  assigned_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type LeadListResponse = {
  items: Lead[];
  total: number;
};

export type LeadCreateBody = {
  pack_id: string;
  name: string;
  phone?: string | null;
  email?: string | null;
  source?: string | null;
  summary?: string | null;
  budget_range?: string | null;
  urgency?: string | null;
  client_id?: string | null;
  pipeline_stage?: string | null;
  due_date?: string | null;
  deal_value?: number | null;
  assigned_user_id?: string | null;
};

export type LeadUpdateBody = {
  name?: string | null;
  phone?: string | null;
  email?: string | null;
  source?: string | null;
  status?: string | null;
  summary?: string | null;
  budget_range?: string | null;
  urgency?: string | null;
  client_id?: string | null;
  pipeline_stage?: string | null;
  due_date?: string | null;
  deal_value?: number | null;
  assigned_user_id?: string | null;
};

/** Public lead capture payload (used by builder sites). */
export type PublicLeadCaptureBody = {
  name: string;
  email?: string | null;
  phone?: string | null;
  summary?: string | null;
  website?: string | null; // honeypot
};

export type PublicLeadCaptureResponse = {
  lead_id: string;
};

/** Builder projects. API: /api/v1/builder */
export type BuilderProject = {
  id: string;
  pack_id: string;
  user_id: string;
  name: string;
  files: Record<string, string>;
  messages: Array<{ role: string; content: string; files_snapshot?: Record<string, string> }>;
  published_files?: Record<string, string> | null;
  live_url: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export type BuilderProjectList = {
  items: BuilderProject[];
  total: number;
};

/** Pack gates (section unlock status). */
export type GateStatus = {
  passed: boolean;
  message: string | null;
};

export type SectionUnlock = {
  unlocked: boolean;
  reason: string | null;
};

export type PackGatesResponse = {
  pack_gate: GateStatus;
  paywall_gate: GateStatus;
  day7_gate: GateStatus;
  day8_gate: GateStatus;
  current_day: number | null;
  has_sprint: boolean;
  sections: Record<string, SectionUnlock>;
};
