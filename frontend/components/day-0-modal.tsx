"use client";

import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, ChevronRight, X } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { SearchInput } from "@/components/ui/search-input";
import { Spinner } from "@/components/ui/page-loader";
import { BrandPreviewModal } from "@/components/brand-preview-modal";
import { OnboardingChoiceButtons } from "@/components/onboarding-chat";
import { packs } from "@/api_requests/packs";
import { sprintApi } from "@/api_requests/sprint";
import { dispatchPackRefresh } from "@/lib/pack-refresh-events";
import type { Pack, ExtractBrandResponse } from "@/types/api-types";

const USP_CATEGORIES = [
  "Faster",
  "More reliable",
  "Better quality",
  "More specialised",
  "Better experience",
  "Better value",
  "Other",
];

type Day0StepConfig =
  | { key: "has_existing_brand"; label: string; required: true; type: "choice" }
  | { key: "brand_url"; label: string; required: true; type: "url" }
  | { key: string; label: string; placeholder?: string; required?: boolean; type: "input" | "select" | "textarea" };

const STEP_CHOICE: Day0StepConfig = {
  key: "has_existing_brand",
  label: "Is this an existing brand?",
  required: true,
  type: "choice",
};

const STEP_WEBSITE_URL: Day0StepConfig = {
  key: "brand_url",
  label: "Enter your website URL",
  required: true,
  type: "url",
};

const DAY0_STEPS_AFTER_CHOICE: Day0StepConfig[] = [
  {
    key: "brand_name",
    label: "What's your brand name?",
    placeholder: "e.g. Acme Co",
    required: true,
    type: "input",
  },
  {
    key: "primary_cta",
    label: "What's your primary call-to-action?",
    placeholder: "e.g. Book a call",
    required: true,
    type: "input",
  },
  {
    key: "usp_category",
    label: "Which USP category fits you best?",
    placeholder: "Select…",
    required: false,
    type: "select",
  },
  {
    key: "usp_statement",
    label: "Why choose you over the obvious alternatives?",
    placeholder: "e.g. We deliver in half the time",
    required: true,
    type: "input",
  },
  {
    key: "usp_proof",
    label: "What proof point makes that true? (optional)",
    placeholder: "e.g. 200+ projects delivered on time",
    required: false,
    type: "input",
  },
  {
    key: "proof_text",
    label: "Any additional proof or testimonials? (optional)",
    placeholder: "Additional proof or testimonials",
    required: false,
    type: "textarea",
  },
];

function getStepValue(stepConfig: Day0StepConfig, values: Record<string, string>): string {
  const key = stepConfig.key;
  if (key === "has_existing_brand") return values.has_existing_brand ?? "";
  if (key === "brand_url") return values.brand_url ?? "";
  if (key === "brand_name") return values.brand_name ?? "";
  if (key === "primary_cta") return values.primary_cta ?? "";
  if (key === "usp_category") return values.usp_category ?? "";
  if (key === "usp_statement") return values.usp_statement ?? "";
  if (key === "usp_proof") return values.usp_proof ?? "";
  if (key === "proof_text") return values.proof_text ?? "";
  return "";
}

export function Day0Modal({
  open,
  onClose,
  packId,
  onComplete,
  onGoToNextStep,
}: {
  open: boolean;
  onClose: () => void;
  packId: string;
  onComplete?: () => void;
  onGoToNextStep?: () => void;
}) {
  const [pack, setPack] = useState<Pack | null>(null);
  const [sprintId, setSprintId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState(0);
  const [values, setValues] = useState<Record<string, string>>({
    has_existing_brand: "",
    brand_url: "",
    brand_name: "",
    primary_cta: "",
    usp_category: "",
    usp_statement: "",
    usp_proof: "",
    proof_text: "",
  });
  const [input, setInput] = useState("");
  const [extractedBrandData, setExtractedBrandData] = useState<ExtractBrandResponse | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const hasExistingBrand = values.has_existing_brand === "yes";
  const step0AlreadyComplete = !!pack?.day_0_completed_at;
  const steps = useMemo<Day0StepConfig[]>(() => {
    if (step0AlreadyComplete) return DAY0_STEPS_AFTER_CHOICE;
    return [STEP_CHOICE, ...(hasExistingBrand ? [STEP_WEBSITE_URL] : []), ...DAY0_STEPS_AFTER_CHOICE];
  }, [step0AlreadyComplete, hasExistingBrand]);
  const totalSteps = steps.length;
  const currentStep = steps[step];
  const isLastStep = step === totalSteps - 1;
  const progressPercent = totalSteps > 0 ? Math.round(((step + 1) / totalSteps) * 100) : 0;

  useEffect(() => {
    if (!open || !packId) return;
    setLoading(true);
    setError("");
    setStep(0);
    Promise.all([packs.get(packId), sprintApi.getSprint(packId)])
      .then(([p, s]) => {
        setPack(p);
        setSprintId(s?.id ?? null);
        const oa = p.onboarding_answers || {};
        const existingBrand = (typeof oa.has_existing_brand === "string" ? oa.has_existing_brand : "") as string;
        const brandUrl = (typeof oa.brand_url === "string" ? oa.brand_url : "") as string;
        setValues({
          has_existing_brand: existingBrand,
          brand_url: brandUrl,
          brand_name: p.brand_name ?? "",
          primary_cta: p.primary_cta ?? "",
          usp_category: p.usp_category ?? "",
          usp_statement: p.usp_statement ?? "",
          usp_proof: p.usp_proof ?? "",
          proof_text: p.proof_text ?? "",
        });
        setInput(existingBrand);
      })
      .catch(() => setError("Pack not found"))
      .finally(() => setLoading(false));
  }, [open, packId]);

  useEffect(() => {
    const current = steps[step];
    if (current) setInput(getStepValue(current, values));
  }, [step, values, steps]);

  const handleChoice = async (value: string) => {
    setError("");
    setSaving(true);
    try {
      const updated = await packs.patch(packId, {
        onboarding_answers: { has_existing_brand: value },
      });
      setPack(updated);
      setValues((prev) => ({ ...prev, has_existing_brand: value }));
      setStep(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save brand type");
    } finally {
      setSaving(false);
    }
  };

  const handlePreviewConfirm = async (editedData: ExtractBrandResponse) => {
    setExtractedBrandData(editedData);
    setValues((prev) => ({
      ...prev,
      brand_name: editedData.brand_name?.trim() || prev.brand_name,
    }));
    setSaving(true);
    try {
      await packs.patch(packId, {
        onboarding_answers: {
          ...(values.brand_url && { brand_url: values.brand_url }),
          extracted_brand: JSON.stringify(editedData),
        },
      });
      setShowPreviewModal(false);
      setStep((s) => s + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save edits");
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!currentStep) return;

    const value = input.trim();
    if (currentStep.required && !value) {
      setError(
        currentStep.type === "choice"
          ? "Please choose an option"
          : `Please enter ${currentStep.label.toLowerCase()}`
      );
      return;
    }

    if (currentStep.type === "url" && currentStep.key === "brand_url") {
      setSaving(true);
      setValues((prev) => ({ ...prev, brand_url: value }));
      try {
        const res = await packs.extractBrand(packId, {
          input_type: "url",
          url: value,
        });
        setExtractedBrandData(res);
        const extractedPayload = {
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
        };
        await packs.patch(packId, {
          onboarding_answers: {
            brand_url: value,
            extracted_brand: JSON.stringify(extractedPayload),
          },
        });
        setShowPreviewModal(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Extraction failed");
        setInput(value);
      } finally {
        setSaving(false);
      }
      return;
    }

    const nextValues = { ...values, [currentStep.key]: value };

    if (!isLastStep) {
      setValues(nextValues);
      setStep((s) => s + 1);
      const nextStepConfig = steps[step + 1];
      if (nextStepConfig) setInput(getStepValue(nextStepConfig, nextValues));
      return;
    }
    if (
      !nextValues.brand_name?.trim() ||
      !nextValues.primary_cta?.trim() ||
      !nextValues.usp_statement?.trim()
    ) {
      setError("Brand name, Primary CTA, and USP statement are required.");
      return;
    }

    setSaving(true);
    try {
      const patchBody: Parameters<typeof packs.patch>[1] = {
        brand_name: nextValues.brand_name.trim(),
        primary_cta: nextValues.primary_cta.trim(),
        usp_category: nextValues.usp_category?.trim() || undefined,
        usp_statement: nextValues.usp_statement.trim(),
        usp_proof: nextValues.usp_proof?.trim() || undefined,
        proof_text: nextValues.proof_text?.trim() || undefined,
      };
      if (nextValues.has_existing_brand === "yes" || nextValues.has_existing_brand === "no") {
        const oa: Record<string, string> = { has_existing_brand: nextValues.has_existing_brand };
        if (nextValues.brand_name?.trim()) oa.brand_name = nextValues.brand_name.trim();
        if (nextValues.primary_cta?.trim()) oa.primary_cta = nextValues.primary_cta.trim();
        if (nextValues.usp_statement?.trim()) oa.usp_statement = nextValues.usp_statement.trim();
        patchBody.onboarding_answers = oa;
      }
      const updated = await packs.patch(packId, patchBody);
      setPack(updated);
      if (updated.day_0_completed_at) {
        try {
          if (sprintId) {
            await sprintApi.completeDay(
              packId,
              sprintId,
              0,
              undefined,
              { suppressPackRefresh: true },
            );
          }
          dispatchPackRefresh({
            packId,
            scopes: [
              "summary",
              "today-tasks",
              "next-action",
              "gates",
              "sprint",
            ],
          });
          if (!onGoToNextStep) onComplete?.();
        } catch (completeErr) {
          setError(
            completeErr instanceof Error
              ? completeErr.message
              : "Step 0 saved, but finishing the sprint step failed. Try again from the pack."
          );
          return;
        }
      }
      if (!updated.day_0_completed_at) {
        onClose();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 p-4 pointer-events-none">
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.2 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="day0-modal-title"
          className="pointer-events-auto w-full max-w-[600px] rounded-2xl border border-border bg-card shadow shadow-black/10"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="relative p-7 sm:p-9">
            <button
              type="button"
              onClick={onClose}
              className="absolute right-4 top-4 p-1.5 rounded-lg text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
            <h2
              id="day0-modal-title"
              className="font-heading text-2xl font-bold text-foreground pr-10"
            >
              Step 0 setup
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Brand name, Primary CTA, and USP are required. Proof is optional.
              Finish these to complete Step 0.
            </p>

            {loading ? (
              <div className="mt-6 min-h-[220px] flex items-center">
                <p className="text-sm text-muted-foreground">Loading…</p>
              </div>
            ) : error && !pack ? (
              <div className="mt-6 min-h-[220px] flex items-center">
                <p
                  className="text-sm text-red-600 dark:text-red-400"
                  role="alert"
                >
                  {error}
                </p>
              </div>
            ) : step0AlreadyComplete ? (
              <div className="mt-6 space-y-4">
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                  <Check className="h-5 w-5 shrink-0" />
                  <span className="text-sm font-medium">
                    Step 0 complete
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Your brand basics are saved. You can move straight into Step 1.
                </p>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button type="button" variant="outline" onClick={onClose} size="md">
                    Close
                  </Button>
                  {onGoToNextStep && (
                    <Button type="button" onClick={onGoToNextStep} size="md">
                      Go to next step
                    </Button>
                  )}
                </div>
                {error && (
                  <p className="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">
                    {error}
                  </p>
                )}
              </div>
            ) : (
              <>
                {/* Progress + big question block (inside container) */}
                <div className="mt-6">
                  <div className="mb-4 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-primary"
                      initial={false}
                      animate={{ width: `${progressPercent}%` }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    Step {step + 1} of {totalSteps}
                  </p>
                  <div className="py-4 px-4">
                    <AnimatePresence mode="wait">
                      {currentStep && (
                        <motion.div
                          key={step}
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -8 }}
                          transition={{ duration: 0.2 }}
                          className="text-center space-y-4"
                        >
                          <h4 className="text-4xl font-semibold text-foreground">
                            {currentStep.label}
                          </h4>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>

                {/* Input + button outside the question container (like onboarding interactiveOnly) */}
                <div className="mt-4">
                  <AnimatePresence mode="wait">
                    {currentStep && (
                      <motion.div
                        key={step}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        transition={{ duration: 0.2 }}
                      >
                        <form onSubmit={handleSubmit}>
                          {currentStep.type === "choice" && (
                            <OnboardingChoiceButtons
                              onChoose={handleChoice}
                              loading={saving}
                              labelYes="Yes, I have a brand"
                              labelNo="No, new brand"
                            />
                          )}
                          {currentStep.type === "url" && currentStep.key === "brand_url" && (
                            <div className="flex flex-col gap-3">
                              <SearchInput
                                type="text"
                                placeholder="e.g. example.com"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                disabled={saving}
                                aria-label="Website URL"
                              />
                              <Button
                                type="submit"
                                disabled={saving || !input.trim()}
                                size="md"
                                className="w-full sm:w-auto"
                              >
                                {saving ? (
                                  <Spinner className="h-5 w-5" />
                                ) : (
                                  <>
                                    Next
                                    <ChevronRight className="h-5 w-5" />
                                  </>
                                )}
                              </Button>
                            </div>
                          )}
                          {currentStep.type === "input" && (
                            <div className="flex flex-col gap-3">
                              <SearchInput
                                placeholder={currentStep.placeholder}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                disabled={saving}
                                aria-label={currentStep.label}
                              />
                              <Button
                                type="submit"
                                disabled={
                                  saving ||
                                  (currentStep.required && !input.trim())
                                }
                                size="md"
                                className="w-full sm:w-auto"
                              >
                                {saving ? (
                                  <Spinner className="h-5 w-5" />
                                ) : (
                                  <>
                                    Next
                                    <ChevronRight className="h-5 w-5" />
                                  </>
                                )}
                              </Button>
                            </div>
                          )}
                          {currentStep.type === "select" && (
                            <div className="flex flex-col gap-3">
                              <select
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                disabled={saving}
                                className="w-full rounded-full border border-border bg-card px-5 py-4 text-base text-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
                                aria-label={currentStep.label}
                              >
                                <option value="">Select…</option>
                                {USP_CATEGORIES.map((c) => (
                                  <option key={c} value={c}>
                                    {c}
                                  </option>
                                ))}
                              </select>
                              <Button
                                type="submit"
                                disabled={saving}
                                size="md"
                                className="w-full sm:w-auto"
                              >
                                {saving ? (
                                  <Spinner className="h-5 w-5" />
                                ) : (
                                  <>
                                    Next
                                    <ChevronRight className="h-5 w-5 ml-1" />
                                  </>
                                )}
                              </Button>
                            </div>
                          )}
                          {currentStep.type === "textarea" && (
                            <div className="flex flex-col gap-3">
                              <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                disabled={saving}
                                placeholder={currentStep.placeholder}
                                className="w-full min-h-[100px] rounded-2xl border border-border bg-card px-5 py-4 text-base text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30 resize-y"
                                aria-label={currentStep.label}
                              />
                              <Button
                                type="submit"
                                disabled={saving}
                                size="md"
                                className="w-full sm:w-auto"
                              >
                                {saving ? (
                                  <Spinner className="h-5 w-5" />
                                ) : (
                                  "Complete Step 0"
                                )}
                              </Button>
                            </div>
                          )}
                        </form>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {error && (
                  <p
                    className="mt-4 text-sm text-red-600 dark:text-red-400"
                    role="alert"
                  >
                    {error}
                  </p>
                )}
              </>
            )}
          </div>
        </motion.div>
      </div>

      <BrandPreviewModal
        open={showPreviewModal}
        data={extractedBrandData}
        onConfirm={handlePreviewConfirm}
        onClose={() => setShowPreviewModal(false)}
        onUploadLogo={(file) =>
          packs.uploadLogo(packId, file).then((r) => r.logo_url)
        }
        loading={saving}
      />
    </>
  );
}
