"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, ChevronRight } from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import { BrandPreview } from "@/components/ui/brand-preview";
import { BrandPreviewModal } from "@/components/brand-preview-modal";
import { CoreConceptLockModal } from "@/components/core-concept-lock-modal";
import {
  packs as packsApi,
  pollPackUntilOnboardingReady,
} from "@/api_requests/packs";
import { me as meApi } from "@/api_requests/me";
import {
  FIRST_MESSAGE,
  PATH_A_INPUT_TYPE_MESSAGE,
  PATH_B_BRAND_NAME_MESSAGE,
  PATH_B_VIBE_MESSAGE,
  BLOCKER_QUESTIONS,
  BLOCKER_COUNT,
  VIBE_CHIP_OPTIONS,
  PACK_TYPE_STEP_LABEL,
  PACK_TYPE_OPTIONS,
} from "@/lib/onboarding";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SearchInput } from "@/components/ui/search-input";
import { Chip } from "@/components/ui/chip";
import { cn } from "@/lib/utils";
import {
  STEP_PACK_NAME,
  STEP_BRAND_QUESTION,
  STEP_PATH_FIRST,
  STEP_PATH_SECOND,
  STEP_BLOCKERS_START,
  STEP_BLOCKERS_END,
  STEP_PACK_TYPE,
  MVP_STEP_KEYS,
  MVP_QUESTIONS,
  MVP_STEP_COUNT,
  getQuestionContent,
  getPackNameSuggestionChips,
} from "@/components/onboarding-chat-steps";

const DEFAULT_PACK_NAME = "My first pack";
const ONBOARDING_INPUT_WRAPPER_CLASS =
  "min-h-[50px] gap-2 px-4 py-2 focus-within:scale-[1.02]";
const ONBOARDING_INPUT_ROW_CLASS =
  "mx-auto flex w-full max-w-[460px] items-center gap-2";
const ONBOARDING_INPUT_CLASS = "text-sm";

export function formatMessageTime() {
  return new Date().toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

export type OnboardingChatState = {
  step: number;
  answers: Record<string, string>;
  answerTimes: Record<string, string>;
  input: string;
  setInput: (v: string) => void;
  loading: boolean;
  error: string;
  selectedPackType: string | null;
  handleSend: (e: React.FormEvent) => Promise<void>;
  handleChoice: (value: string) => Promise<void>;
  handlePathAInputType: (type: "url" | "paste" | "logo") => void;
  handlePathBVibeToggle: (vibe: string) => void;
  handleBrandPreviewConfirm: (
    finalData: import("@/types/api-types").ExtractBrandResponse,
  ) => void;
  handlePreviewModalClose: () => void;
  handlePackTypeChoice: (packType: string) => Promise<void>;
  handleCoreConceptConfirm: (coreConcept: string) => Promise<void>;
  botMessageTimesRef: React.MutableRefObject<Record<number, string>>;
  packId: string | null;
  extractedBrandData: import("@/types/api-types").ExtractBrandResponse | null;
  showPreviewModal: boolean;
  showCoreConceptModal: boolean;
  completedPack: import("@/types/api-types").Pack | null;
  onboardingProgress: string;
  retryFailedStep: (() => Promise<void>) | null;
};

export function useOnboardingChat(options: {
  onComplete?: (packId: string) => void;
  initialPackId?: string | null;
  mvpOnly?: boolean;
}): OnboardingChatState {
  const router = useRouter();
  const mvpOnly = options.mvpOnly === true;
  const [packId, setPackId] = useState<string | null>(
    options.initialPackId ?? null,
  );
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [answerTimes, setAnswerTimes] = useState<Record<string, string>>({});
  const [step, setStep] = useState(0);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [extractedBrandData, setExtractedBrandData] = useState<
    import("@/types/api-types").ExtractBrandResponse | null
  >(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [showCoreConceptModal, setShowCoreConceptModal] = useState(false);
  const [completedPack, setCompletedPack] = useState<
    import("@/types/api-types").Pack | null
  >(null);
  const [selectedPackType, setSelectedPackType] = useState<string | null>(null);
  const [onboardingProgress, setOnboardingProgress] = useState("");
  const [retryFailedStep, setRetryFailedStep] = useState<
    (() => Promise<void>) | null
  >(null);
  const botMessageTimesRef = useRef<Record<number, string>>({});
  const packTypeSubmittingRef = useRef(false);

  const hasExistingBrand = answers.has_existing_brand === "yes";
  const brandInputType = answers.brand_input_type as
    | "url"
    | "paste"
    | "logo"
    | undefined;

  const ensurePack = async (): Promise<string> => {
    if (packId) return packId;
    const packName = answers.pack_name || DEFAULT_PACK_NAME;
    const pack = await packsApi.create(packName);
    setPackId(pack.id);
    return pack.id;
  };

  const handleChoice = async (value: string) => {
    setError("");
    if (step === STEP_BRAND_QUESTION) {
      setAnswers((prev) => ({ ...prev, has_existing_brand: value }));
      setAnswerTimes((prev) => ({
        ...prev,
        has_existing_brand: formatMessageTime(),
      }));
      setLoading(true);
      try {
        await ensurePack();
        setStep(STEP_PATH_FIRST);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
    }
  };

  const handlePathAInputType = (type: "url" | "paste" | "logo") => {
    setAnswers((prev) => ({ ...prev, brand_input_type: type }));
    setStep(STEP_PATH_SECOND);
  };

  const selectedVibes = (
    answers.vibe_chips ? JSON.parse(answers.vibe_chips) : []
  ) as string[];
  const handlePathBVibeToggle = (vibe: string) => {
    const next = selectedVibes.includes(vibe)
      ? selectedVibes.filter((v) => v !== vibe)
      : [...selectedVibes, vibe];
    setAnswers((prev) => ({ ...prev, vibe_chips: JSON.stringify(next) }));
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    setError("");

    // MVP flow: 4 steps then landing-complete
    if (mvpOnly) {
      if (!trimmed) return;
      const key = MVP_STEP_KEYS[step];
      setAnswers((prev) => ({ ...prev, [key]: trimmed }));
      setAnswerTimes((prev) => ({ ...prev, [key]: formatMessageTime() }));
      setInput("");
      if (step < MVP_STEP_COUNT - 1) {
        setStep(step + 1);
        return;
      }
      setLoading(true);
      try {
        const payload = {
          pack_name: trimmed,
          what_do_you_sell: answers.what_do_you_sell || "",
          who_is_it_for: answers.who_is_it_for || "",
          where_are_you_based: answers.where_are_you_based || "",
        };
        const final = await meApi.landingComplete(payload);
        if (options.onComplete) options.onComplete(final.pack_id);
        else router.push(final.redirect);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
      return;
    }

    // Pack name step
    if (step === STEP_PACK_NAME) {
      if (!trimmed) return;
      setAnswers((prev) => ({ ...prev, pack_name: trimmed }));
      setAnswerTimes((prev) => ({ ...prev, pack_name: formatMessageTime() }));
      setInput("");
      setStep(STEP_BRAND_QUESTION);
      return;
    }

    if (step === STEP_PATH_FIRST && !hasExistingBrand) {
      if (!trimmed) return;
      setAnswers((prev) => ({ ...prev, brand_name: trimmed }));
      setAnswerTimes((prev) => ({ ...prev, brand_name: formatMessageTime() }));
      setInput("");
      setStep(STEP_PATH_SECOND);
      return;
    }

    // Path A: handle URL input directly at STEP_PATH_FIRST
    if (step === STEP_PATH_FIRST && hasExistingBrand) {
      if (!trimmed) return;
      setLoading(true);
      const id = packId || (await ensurePack());
      setAnswers((prev) => ({
        ...prev,
        brand_url: trimmed,
        brand_input_type: "url",
      }));
      setInput("");
      try {
        const res = await packsApi.extractBrand(id, {
          input_type: "url",
          url: trimmed,
        });
        // Store the full extracted data for preview
        setExtractedBrandData(res);
        // Store minimal data in answers for now
        setAnswers((prev) => ({
          ...prev,
          extracted_brand: JSON.stringify({
            brand_name: res.brand_name,
            offer_cues: res.offer_cues,
            tagline: res.tagline,
            description: res.description,
            industry: res.industry,
            contact_info: res.contact_info,
            social_links: res.social_links,
            logo_url: res.logo_url,
            color_candidates: res.color_candidates,
            raw_extract: res.raw_extract,
          }),
        }));
        // Show preview modal instead of changing step
        setShowPreviewModal(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Extraction failed");
        setInput(trimmed);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (step === STEP_PATH_SECOND && !hasExistingBrand) {
      if (selectedVibes.length === 0) {
        setError("Pick at least one vibe.");
        return;
      }
      setLoading(true);
      const id = packId || (await ensurePack());
      const name = answers.brand_name || "My Brand";
      try {
        const res = await packsApi.generateStarterBrand(id, {
          brand_name: name,
          vibe_chips: selectedVibes,
        });
        setAnswers((prev) => ({
          ...prev,
          wordmark_svg_or_url: res.wordmark_svg_or_url,
          palette: JSON.stringify(res.palette),
        }));
        setStep(STEP_BLOCKERS_START);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Generation failed");
      } finally {
        setLoading(false);
      }
      return;
    }

    if (step >= STEP_BLOCKERS_START && step <= STEP_BLOCKERS_END) {
      const blockerIndex = step - STEP_BLOCKERS_START;
      const key = BLOCKER_QUESTIONS[blockerIndex].key;
      if (!trimmed) return;
      const nextAnswers = { ...answers, [key]: trimmed };
      setAnswerTimes((prev) => ({ ...prev, [key]: formatMessageTime() }));
      setAnswers(nextAnswers);
      setInput("");
      if (step === STEP_BLOCKERS_END) {
        setStep(STEP_PACK_TYPE);
      } else {
        setStep(step + 1);
      }
      return;
    }
  };

  const handlePackTypeChoice = async (packType: string) => {
    if (packTypeSubmittingRef.current) return;
    packTypeSubmittingRef.current = true;
    setError("");
    setRetryFailedStep(null);
    setOnboardingProgress("");
    setSelectedPackType(packType);
    setLoading(true);
    try {
      const id = packId!;
      const nextAnswers = { ...answers, pack_type: packType };
      await packsApi.submitOnboarding(id, nextAnswers);
      const res = await packsApi.completeOnboarding(id);
      if ("pack" in res && res.pack) {
        setCompletedPack(res.pack);
      } else if (
        "status" in res &&
        res.status === "processing" &&
        res.pack_id
      ) {
        setOnboardingProgress("Queued. Preparing your brand setup...");
        const pack = await pollPackUntilOnboardingReady(res.pack_id, {
          onProgress: (_status, message) => setOnboardingProgress(message),
        });
        setCompletedPack(pack);
      }
      setOnboardingProgress("");
      setShowCoreConceptModal(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setRetryFailedStep(() => () => handlePackTypeChoice(packType));
      setOnboardingProgress("");
    } finally {
      packTypeSubmittingRef.current = false;
      setLoading(false);
      setSelectedPackType(null);
    }
  };

  const handleCoreConceptConfirm = async (coreConcept: string) => {
    if (!completedPack) return;
    setError("");
    setLoading(true);
    try {
      await packsApi.patch(completedPack.id, {
        core_concept: coreConcept.trim() || null,
      });
      setShowCoreConceptModal(false);
      setCompletedPack(null);
      if (options.onComplete) options.onComplete(completedPack.id);
      else router.push(`/chat?pack=${completedPack.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const handleBrandPreviewConfirm = (
    finalData: import("@/types/api-types").ExtractBrandResponse,
  ) => {
    setError("");
    setExtractedBrandData(finalData);
    setAnswers((prev) => ({
      ...prev,
      extracted_brand: JSON.stringify(finalData),
    }));
    setShowPreviewModal(false);
    setStep(STEP_BLOCKERS_START);
  };

  const handlePreviewModalClose = () => {
    // Allow closing without confirming (user can retry)
    setShowPreviewModal(false);
  };

  return {
    step,
    answers,
    answerTimes,
    input,
    setInput,
    loading,
    error,
    selectedPackType,
    onboardingProgress,
    retryFailedStep,
    handleSend,
    handleChoice,
    handlePathAInputType,
    handlePathBVibeToggle,
    handleBrandPreviewConfirm,
    handlePreviewModalClose,
    handlePackTypeChoice,
    handleCoreConceptConfirm,
    botMessageTimesRef,
    packId,
    extractedBrandData,
    showPreviewModal,
    showCoreConceptModal,
    completedPack,
  };
}

/** Two-button choice (e.g. Yes / No). */
export function OnboardingChoiceButtons({
  onChoose,
  loading,
  labelYes = "Yes, I have a brand",
  labelNo = "No, new brand",
}: {
  onChoose: (value: string) => void;
  loading?: boolean;
  labelYes?: string;
  labelNo?: string;
}) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 justify-center items-center w-full mt-8">
      <Button
        type="button"
        variant="default"
        size="lg"
        onClick={() => onChoose("yes")}
        disabled={loading}
        aria-label={labelYes}
        className="w-full sm:w-auto min-w-[200px] p-8 rounded-full"
      >
        {labelYes}
      </Button>
      <Button
        type="button"
        variant="default"
        size="lg"
        onClick={() => onChoose("no")}
        disabled={loading}
        aria-label={labelNo}
        className="w-full sm:w-auto min-w-[200px] p-8 rounded-full bg-white text-black"
      >
        {labelNo}
      </Button>
    </div>
  );
}

/** Path A: website URL input field */
export function OnboardingPathAInputType({
  onSubmit,
  input,
  setInput,
  loading,
}: {
  onSubmit: (e: React.FormEvent) => void;
  input: string;
  setInput: (v: string) => void;
  loading: boolean;
}) {
  return (
    <form onSubmit={onSubmit} className={ONBOARDING_INPUT_ROW_CLASS}>
      <SearchInput
        type="text"
        placeholder="e.g. example.com"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        disabled={loading}
        aria-label="Website URL"
        wrapperClassName={ONBOARDING_INPUT_WRAPPER_CLASS}
        className={ONBOARDING_INPUT_CLASS}
      />
      <Button
        type="submit"
        disabled={loading || !input.trim()}
        size="sm"
        className="h-[50px] w-[50px] rounded-full p-0 shrink-0"
      >
        {loading ? (
          <Spinner className="h-5 w-5" />
        ) : (
          <ChevronRight className="h-5 w-5" />
        )}
      </Button>
    </form>
  );
}

/** Path B: vibe chips multi-select. */
export function OnboardingPathBVibes({
  selected,
  onToggle,
  disabled,
}: {
  selected: string[];
  onToggle: (vibe: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {VIBE_CHIP_OPTIONS.map((vibe) => (
        <Chip
          key={vibe}
          size="md"
          onClick={() => !disabled && onToggle(vibe)}
          className={cn(
            "cursor-pointer",
            selected.includes(vibe) &&
              "bg-foreground text-background border-foreground",
          )}
        >
          {vibe}
        </Chip>
      ))}
    </div>
  );
}

function getOnboardingTotalSteps(mvpOnly: boolean) {
  return mvpOnly ? MVP_STEP_COUNT : 4 + BLOCKER_COUNT + 1;
}

function getOnboardingStepIndex(step: number, mvpOnly: boolean) {
  if (mvpOnly) {
    return Math.min(Math.max(step, 0), MVP_STEP_COUNT - 1);
  }
  const maxIndex = getOnboardingTotalSteps(false) - 1;
  return Math.min(Math.max(step, 0), maxIndex);
}

export function OnboardingStepIndicators({
  step,
  mvpOnly = false,
  className,
}: {
  step: number;
  mvpOnly?: boolean;
  className?: string;
}) {
  const totalSteps = getOnboardingTotalSteps(mvpOnly);
  const activeIndex = getOnboardingStepIndex(step, mvpOnly);

  return (
    <div className={cn("flex items-center justify-center gap-2", className)}>
      {Array.from({ length: totalSteps }).map((_, index) => (
        <span
          key={index}
          className={cn(
            "h-1.5 w-1.5 rounded-full transition-all",
            index === activeIndex ? "w-3 bg-foreground/90" : "bg-foreground/25",
          )}
        />
      ))}
    </div>
  );
}

/** Single-slide view: current step only. For modal use. */
export function OnboardingSlideView({
  step,
  answers,
  answerTimes,
  loading,
  error,
  selectedPackType = null,
  botMessageTimesRef,
  onChoice,
  onPathAInputType,
  onPathBVibeToggle,
  onPackTypeChoose,
  input,
  setInput,
  onSubmit,
  className,
  modalContentOnly,
  interactiveOnly,
  questionOnly,
  mvpOnly = false,
  onboardingProgress = "",
  retryFailedStep = null,
}: {
  step: number;
  answers: Record<string, string>;
  answerTimes: Record<string, string>;
  loading: boolean;
  error: string;
  selectedPackType?: string | null;
  botMessageTimesRef: React.MutableRefObject<Record<number, string>>;
  onChoice: (value: string) => void;
  onPathAInputType: (type: "url" | "paste" | "logo") => void;
  onPathBVibeToggle: (vibe: string) => void;
  onPackTypeChoose?: (packType: string) => void;
  input: string;
  setInput: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  className?: string;
  modalContentOnly?: boolean;
  interactiveOnly?: boolean;
  questionOnly?: boolean;
  mvpOnly?: boolean;
  onboardingProgress?: string;
  retryFailedStep?: (() => Promise<void>) | null;
}) {
  const hasExistingBrand = answers.has_existing_brand === "yes";
  const brandInputType = answers.brand_input_type as
    | "url"
    | "paste"
    | "logo"
    | undefined;
  const selectedVibes = (
    answers.vibe_chips ? JSON.parse(answers.vibe_chips) : []
  ) as string[];
  const totalSteps = getOnboardingTotalSteps(mvpOnly); // pack name + brand question + path steps + blockers + pack type
  const progressPercent =
    totalSteps > 0 ? Math.round(((step + 1) / totalSteps) * 100) : 0;

  let botMessage = FIRST_MESSAGE;
  if (mvpOnly && step >= 0 && step < MVP_STEP_COUNT) {
    botMessage = MVP_QUESTIONS[step].label;
  } else if (step === STEP_PATH_FIRST) {
    botMessage = hasExistingBrand
      ? PATH_A_INPUT_TYPE_MESSAGE
      : PATH_B_BRAND_NAME_MESSAGE;
  } else if (step === STEP_PATH_SECOND) {
    botMessage = hasExistingBrand
      ? `Enter your ${brandInputType === "url" ? "website URL" : brandInputType === "paste" ? "pasted copy" : "logo"} below.`
      : PATH_B_VIBE_MESSAGE;
  } else if (step === STEP_PACK_TYPE) {
    botMessage = PACK_TYPE_STEP_LABEL;
  } else if (step >= STEP_BLOCKERS_START && step <= STEP_BLOCKERS_END) {
    const blockerLabel = BLOCKER_QUESTIONS[step - STEP_BLOCKERS_START].label;
    if (step === STEP_BLOCKERS_START) {
      const summary =
        hasExistingBrand && answers.extracted_brand
          ? (() => {
              try {
                const o = JSON.parse(answers.extracted_brand) as {
                  brand_name?: string;
                };
                return o.brand_name ? `We found: ${o.brand_name}. ` : "";
              } catch {
                return "";
              }
            })()
          : !hasExistingBrand && answers.brand_name
            ? `Starter look for "${answers.brand_name}" is ready. `
            : "";
      botMessage = summary ? `${summary}Now: ${blockerLabel}` : blockerLabel;
    } else {
      botMessage = blockerLabel;
    }
  }

  const showMvpInput = mvpOnly && step >= 0 && step < MVP_STEP_COUNT;
  const showPackNameInput = !mvpOnly && step === STEP_PACK_NAME;
  const showChoiceButtons = !mvpOnly && step === STEP_BRAND_QUESTION;
  const showPathAInputType =
    !mvpOnly && step === STEP_PATH_FIRST && hasExistingBrand;
  const showPathBNameInput =
    !mvpOnly && step === STEP_PATH_FIRST && !hasExistingBrand;
  const showPathBVibes =
    !mvpOnly && step === STEP_PATH_SECOND && !hasExistingBrand;
  const showBlockerInput =
    !mvpOnly && step >= STEP_BLOCKERS_START && step <= STEP_BLOCKERS_END;
  const showPackTypeChoice = !mvpOnly && step === STEP_PACK_TYPE;
  const showForm =
    showMvpInput ||
    showPackNameInput ||
    showPathBNameInput ||
    showBlockerInput ||
    showPackTypeChoice ||
    (showPathBVibes && selectedVibes.length > 0);

  const userAnswer =
    step === STEP_PACK_NAME
      ? answers.pack_name
      : step === STEP_BRAND_QUESTION
        ? answers.has_existing_brand
          ? "Yes, I have a brand"
          : "No, new brand"
        : step === STEP_PATH_FIRST && !hasExistingBrand
          ? answers.brand_name
          : step >= STEP_BLOCKERS_START && step <= STEP_BLOCKERS_END
            ? answers[BLOCKER_QUESTIONS[step - STEP_BLOCKERS_START].key]
            : step === STEP_PACK_TYPE
              ? (PACK_TYPE_OPTIONS.find((o) => o.value === answers.pack_type)
                  ?.label ?? null)
              : step === STEP_PATH_SECOND && hasExistingBrand
                ? answers.brand_url || answers.pasted_copy
                : step === STEP_PATH_SECOND && !hasExistingBrand
                  ? selectedVibes.join(", ")
                  : null;

  if (questionOnly) {
    return (
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
          className="text-center space-y-4"
        >
          <h4 className="text-2xl sm:text-3xl font-semibold text-foreground">
            {mvpOnly && step < MVP_STEP_COUNT
              ? MVP_QUESTIONS[step].label
              : getQuestionContent(step, hasExistingBrand).question}
          </h4>
          {mvpOnly && step < MVP_STEP_COUNT && MVP_QUESTIONS[step].subLabel && (
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              {MVP_QUESTIONS[step].subLabel}
            </p>
          )}
          {!mvpOnly && getQuestionContent(step, hasExistingBrand).helper && (
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              {getQuestionContent(step, hasExistingBrand).helper}
            </p>
          )}
        </motion.div>
      </AnimatePresence>
    );
  }

  // If only interactive content is requested, return just that
  if (interactiveOnly) {
    return (
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {showMvpInput && (
            <div className="flex flex-col gap-3 items-center w-full max-w-[460px] mx-auto">
              {mvpOnly &&
                step === 3 &&
                (() => {
                  const packNameChips = getPackNameSuggestionChips(answers);
                  return packNameChips.length > 0 ? (
                    <div className="flex flex-wrap gap-2 justify-center">
                      {packNameChips.map((chip) => (
                        <Chip
                          key={chip.value}
                          size="md"
                          onClick={() => !loading && setInput(chip.value)}
                          className="cursor-pointer"
                        >
                          {chip.label}
                        </Chip>
                      ))}
                    </div>
                  ) : null;
                })()}
              <form onSubmit={onSubmit} className={ONBOARDING_INPUT_ROW_CLASS}>
                <SearchInput
                  placeholder={MVP_QUESTIONS[step].placeholder}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                  aria-label={MVP_QUESTIONS[step].label}
                  wrapperClassName={ONBOARDING_INPUT_WRAPPER_CLASS}
                  className={ONBOARDING_INPUT_CLASS}
                />
                <Button
                  type="submit"
                  disabled={loading || !input.trim()}
                  size="sm"
                  className="h-[50px] w-[50px] rounded-full p-0 shrink-0"
                >
                  {loading ? (
                    <Spinner className="h-5 w-5" />
                  ) : (
                    <ChevronRight className="h-5 w-5" />
                  )}
                </Button>
              </form>
            </div>
          )}
          {showPackNameInput && (
            <form onSubmit={onSubmit} className={ONBOARDING_INPUT_ROW_CLASS}>
              <SearchInput
                placeholder="My Campaign Pack"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                aria-label="Pack name"
                wrapperClassName={ONBOARDING_INPUT_WRAPPER_CLASS}
                className={ONBOARDING_INPUT_CLASS}
              />
              <Button
                type="submit"
                disabled={loading || !input.trim()}
                size="sm"
                className="h-[50px] w-[50px] rounded-full p-0 shrink-0"
              >
                {loading ? (
                  <Spinner className="h-5 w-5" />
                ) : (
                  <ChevronRight className="h-5 w-5" />
                )}
              </Button>
            </form>
          )}
          {showChoiceButtons && (
            <OnboardingChoiceButtons
              onChoose={onChoice}
              loading={loading}
              labelYes="Yes, I have a brand"
              labelNo="No, new brand"
            />
          )}
          {showPathAInputType && (
            <OnboardingPathAInputType
              onSubmit={onSubmit}
              input={input}
              setInput={setInput}
              loading={loading}
            />
          )}
          {showPathBNameInput && (
            <form onSubmit={onSubmit} className={ONBOARDING_INPUT_ROW_CLASS}>
              <SearchInput
                placeholder="e.g. Acme Co"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                wrapperClassName={ONBOARDING_INPUT_WRAPPER_CLASS}
                className={ONBOARDING_INPUT_CLASS}
              />
              <Button
                type="submit"
                disabled={loading || !input.trim()}
                size="sm"
                className="h-[50px] w-[50px] rounded-full p-0 shrink-0"
              >
                {loading ? (
                  <Spinner className="h-5 w-5" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </form>
          )}
          {showPathBVibes && (
            <div className="space-y-3">
              <OnboardingPathBVibes
                selected={selectedVibes}
                onToggle={onPathBVibeToggle}
                disabled={loading}
              />
              <Button
                type="button"
                onClick={() =>
                  onSubmit({ preventDefault: () => {} } as React.FormEvent)
                }
                disabled={loading || selectedVibes.length === 0}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Spinner className="h-4 w-4 mr-2" />
                    Generating…
                  </>
                ) : (
                  "Continue"
                )}
              </Button>
            </div>
          )}
          {showBlockerInput && (
            <form onSubmit={onSubmit} className={ONBOARDING_INPUT_ROW_CLASS}>
              <SearchInput
                placeholder="Type your answer…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                wrapperClassName={ONBOARDING_INPUT_WRAPPER_CLASS}
                className={ONBOARDING_INPUT_CLASS}
              />
              <Button
                type="submit"
                disabled={loading || !input.trim()}
                size="sm"
                className="h-[50px] w-[50px] rounded-full p-0 shrink-0"
              >
                {loading ? (
                  <Spinner className="h-5 w-5" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </form>
          )}
          {showPackTypeChoice && onPackTypeChoose && (
            <div className="flex flex-col gap-3">
              {PACK_TYPE_OPTIONS.map((opt) => {
                const isSubmitting = selectedPackType === opt.value;
                const isDisabled = loading || selectedPackType !== null;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => onPackTypeChoose(opt.value)}
                    disabled={isDisabled}
                    className={cn(
                      "text-left p-4 rounded-xl border border-border bg-background transition-colors",
                      isSubmitting
                        ? "border-primary/50 bg-muted/30"
                        : "hover:bg-muted/50",
                    )}
                    aria-busy={isSubmitting}
                  >
                    {isSubmitting ? (
                      <span className="font-medium flex items-center gap-2">
                        <Spinner className="h-4 w-4 shrink-0" />
                        Setting up {opt.label}…
                      </span>
                    ) : (
                      <>
                        <span className="font-medium block">{opt.label}</span>
                        <span className="text-sm text-muted-foreground">
                          {opt.description}
                        </span>
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          )}
          {error && (
            <div className="space-y-2">
              <p className="text-sm text-red-400 bg-red-500/10 rounded-xl px-4 py-3 border border-red-500/20">
                {error}
              </p>
              {retryFailedStep && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void retryFailedStep()}
                  disabled={loading}
                >
                  Retry last step
                </Button>
              )}
            </div>
          )}
          {onboardingProgress && (
            <p className="text-sm text-foreground/90 bg-muted rounded-xl px-4 py-3 border border-border flex items-center justify-center gap-2">
              <Spinner className="h-4 w-4" />
              {onboardingProgress}
            </p>
          )}
        </motion.div>
      </AnimatePresence>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn("flex flex-col min-h-0", className)}
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 h-[4px] rounded-full bg-muted overflow-hidden">
          <motion.div
            className="h-[4px] rounded-full bg-foreground"
            initial={false}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          />
        </div>
      </div>

      <div className="flex-1 min-h-0 py-8 px-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="text-center space-y-4"
          >
            <h4 className="text-3xl sm:text-4xl font-semibold text-foreground">
              {mvpOnly && step < MVP_STEP_COUNT
                ? MVP_QUESTIONS[step].label
                : getQuestionContent(step, hasExistingBrand).question}
            </h4>
            {mvpOnly &&
              step < MVP_STEP_COUNT &&
              MVP_QUESTIONS[step].subLabel && (
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  {MVP_QUESTIONS[step].subLabel}
                </p>
              )}
            {!mvpOnly && getQuestionContent(step, hasExistingBrand).helper && (
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                {getQuestionContent(step, hasExistingBrand).helper}
              </p>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
      {(error || onboardingProgress) && (
        <div className="px-4 pb-4 space-y-2">
          {error && (
            <div className="space-y-2 text-center">
              <p className="text-sm text-red-400 bg-red-500/10 rounded-xl px-4 py-3 border border-red-500/20">
                {error}
              </p>
              {retryFailedStep && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void retryFailedStep()}
                  disabled={loading}
                >
                  Retry last step
                </Button>
              )}
            </div>
          )}
          {onboardingProgress && (
            <p className="text-sm text-foreground/90 bg-muted rounded-xl px-4 py-3 border border-border flex items-center justify-center gap-2">
              <Spinner className="h-4 w-4" />
              {onboardingProgress}
            </p>
          )}
        </div>
      )}
    </motion.div>
  );
}

/** Full chat with internal form (e.g. standalone onboarding page). */
export function OnboardingChat({
  onComplete,
  initialPackId,
  className,
}: {
  onComplete?: (packId: string) => void;
  initialPackId?: string | null;
  className?: string;
}) {
  const state = useOnboardingChat({ onComplete, initialPackId });
  return (
    <>
      <OnboardingSlideView
        step={state.step}
        answers={state.answers}
        answerTimes={state.answerTimes}
        loading={state.loading}
        error={state.error}
        selectedPackType={state.selectedPackType}
        botMessageTimesRef={state.botMessageTimesRef}
        onChoice={state.handleChoice}
        onPathAInputType={state.handlePathAInputType}
        onPathBVibeToggle={state.handlePathBVibeToggle}
        onPackTypeChoose={state.handlePackTypeChoice}
        input={state.input}
        setInput={state.setInput}
        onSubmit={state.handleSend}
        className={className}
        onboardingProgress={state.onboardingProgress}
        retryFailedStep={state.retryFailedStep}
      />

      <BrandPreviewModal
        open={state.showPreviewModal}
        data={state.extractedBrandData}
        onConfirm={state.handleBrandPreviewConfirm}
        onClose={state.handlePreviewModalClose}
        onUploadLogo={
          state.packId
            ? (file) =>
                packsApi.uploadLogo(state.packId!, file).then((r) => r.logo_url)
            : undefined
        }
        loading={state.loading}
      />

      <CoreConceptLockModal
        open={state.showCoreConceptModal}
        packId={state.completedPack?.id ?? null}
        initialCoreConcept={state.completedPack?.core_concept ?? null}
        onConfirm={state.handleCoreConceptConfirm}
        loading={state.loading}
      />
    </>
  );
}

export function OnboardingSharedStepLayout({
  step,
  answers,
  answerTimes,
  loading,
  error,
  selectedPackType = null,
  botMessageTimesRef,
  onChoice,
  onPathAInputType,
  onPathBVibeToggle,
  onPackTypeChoose,
  input,
  setInput,
  onSubmit,
  className,
  mvpOnly = false,
  onboardingProgress = "",
  retryFailedStep = null,
}: {
  step: number;
  answers: Record<string, string>;
  answerTimes: Record<string, string>;
  loading: boolean;
  error: string;
  selectedPackType?: string | null;
  botMessageTimesRef: React.MutableRefObject<Record<number, string>>;
  onChoice: (value: string) => void;
  onPathAInputType: (type: "url" | "paste" | "logo") => void;
  onPathBVibeToggle: (vibe: string) => void;
  onPackTypeChoose?: (packType: string) => void;
  input: string;
  setInput: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  className?: string;
  mvpOnly?: boolean;
  onboardingProgress?: string;
  retryFailedStep?: (() => Promise<void>) | null;
}) {
  return (
    <div
      className={cn(
        "w-full max-w-[600px] mx-auto flex flex-col flex-1",
        className,
      )}
    >
      <div className="min-h-[340px] flex flex-col justify-center flex-1">
        <div className="px-4 sm:px-6">
          <OnboardingSlideView
            step={step}
            answers={answers}
            answerTimes={answerTimes}
            loading={loading}
            error={error}
            selectedPackType={selectedPackType}
            botMessageTimesRef={botMessageTimesRef}
            onChoice={onChoice}
            onPathAInputType={onPathAInputType}
            onPathBVibeToggle={onPathBVibeToggle}
            onPackTypeChoose={onPackTypeChoose}
            input={input}
            setInput={setInput}
            onSubmit={onSubmit}
            mvpOnly={mvpOnly}
            questionOnly
          />
        </div>

        <div className="mt-6 px-2 sm:px-4">
          <OnboardingSlideView
            step={step}
            answers={answers}
            answerTimes={answerTimes}
            loading={loading}
            error={error}
            selectedPackType={selectedPackType}
            botMessageTimesRef={botMessageTimesRef}
            onChoice={onChoice}
            onPathAInputType={onPathAInputType}
            onPathBVibeToggle={onPathBVibeToggle}
            onPackTypeChoose={onPackTypeChoose}
            input={input}
            setInput={setInput}
            onSubmit={onSubmit}
            mvpOnly={mvpOnly}
            interactiveOnly
            onboardingProgress={onboardingProgress}
            retryFailedStep={retryFailedStep}
          />
        </div>
      </div>

      <OnboardingStepIndicators
        step={step}
        mvpOnly={mvpOnly}
        className="mt-auto pt-8 pb-6"
      />
    </div>
  );
}
