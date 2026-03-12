"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Select, SelectItem } from "@/components/ui/select";
import { docs as docsApi } from "@/api_requests/docs";
import { FileText, Layers, Sparkles } from "@/components/icons";
import { cn } from "@/lib/utils";
import type {
  DocsDocumentType,
  DocsStartMode,
  DocsTemplate,
  DocsTonePreset,
} from "@/types/api-types";
import { formatDocTypeLabel } from "../_components/docs-utils";

const TONE_OPTIONS: DocsTonePreset[] = [
  "formal",
  "professional",
  "persuasive",
  "concise",
  "warm",
];

const CREATION_MODES = [
  {
    key: "sample",
    label: "AI sample",
    description: "Create a fully populated sample draft that can be edited immediately.",
  },
  {
    key: "blank",
    label: "Blank template",
    description: "Open the template structure as a fresh writing canvas.",
  },
] as const;

function previewTextForSection(template: DocsTemplate, sectionLabel: string): string {
  const docName = template.label;
  if (sectionLabel.toLowerCase().includes("pricing")) {
    return "AI can drop in sample pricing language here so the page feels complete from the first load.";
  }
  if (sectionLabel.toLowerCase().includes("timeline")) {
    return "Add a simple schedule or let the draft generator suggest a realistic rollout sequence.";
  }
  if (sectionLabel.toLowerCase().includes("next")) {
    return "Close with a clear action so the document reads like something ready to send.";
  }
  if (sectionLabel.toLowerCase().includes("summary")) {
    return `Generate an opening summary for this ${docName.toLowerCase()} and refine the wording directly on the page.`;
  }
  return `Start writing ${sectionLabel.toLowerCase()} here, or let AI create a sample version you can revise on the canvas.`;
}

export default function NewDocumentPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const packId = params.packId as string;

  const [templates, setTemplates] = useState<DocsTemplate[]>([]);
  const [selectedType, setSelectedType] = useState<DocsDocumentType>("proposal");
  const [startMode, setStartMode] = useState<DocsStartMode>("template");
  const [tonePreset, setTonePreset] = useState<DocsTonePreset>("professional");
  const [creationMode, setCreationMode] =
    useState<(typeof CREATION_MODES)[number]["key"]>("sample");
  const [submitting, setSubmitting] = useState<null | "sample" | "blank">(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    docsApi.listTemplates(packId).then((items) => {
      setTemplates(items);
      const typeParam = searchParams.get("type") as DocsDocumentType | null;
      const startModeParam = searchParams.get("startMode") as DocsStartMode | null;
      if (typeParam && items.some((item) => item.type === typeParam)) {
        setSelectedType(typeParam);
      }
      if (startModeParam && ["suggested", "template", "notes"].includes(startModeParam)) {
        setStartMode(startModeParam);
        if (startModeParam === "notes") {
          setCreationMode("sample");
        }
      }
    });
  }, [packId, searchParams]);

  const template = useMemo(
    () => templates.find((item) => item.type === selectedType) ?? null,
    [selectedType, templates],
  );

  const createDocument = async (mode: "sample" | "blank") => {
    if (!template) return;
    setSubmitting(mode);
    setError(null);
    try {
      const created = await docsApi.createDocument(packId, {
        type: selectedType,
        tone_preset: tonePreset,
        start_mode: startMode,
      });
      if (mode === "sample") {
        await docsApi.generateDocument(packId, created.id);
      }
      router.push(`/packs/${packId}/docs/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open document");
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="docs-page-body docs-page-body-wide">
      <div className="max-w-3xl">
        <p className="docs-eyebrow">New document</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
          Start from a template, then edit on the page
        </h1>
        <p className="mt-3 text-sm leading-7 text-muted-foreground">
          Docs now opens as a writing canvas. Pick a blueprint, choose whether
          you want a generated sample or a blank template, and the editor opens
          directly on the document.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
        <aside className="docs-panel p-3">
          <div className="px-2 pb-3">
            <p className="docs-eyebrow">Templates</p>
          </div>
          <div className="space-y-1">
            {templates.map((item) => (
              <button
                key={item.type}
                type="button"
                onClick={() => setSelectedType(item.type)}
                className={cn(
                  "docs-template-tile",
                  selectedType === item.type && "docs-template-tile-active",
                )}
              >
                <FileText className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <span>
                  <span className="block text-sm font-medium text-foreground">
                    {item.label}
                  </span>
                  <span className="block text-xs leading-5 text-muted-foreground">
                    {item.purpose}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <div className="space-y-4">
          <div className="docs-panel overflow-hidden">
            <div className="border-b border-border/50 px-6 py-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="docs-eyebrow">Template preview</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
                    {template?.label || "Document template"}
                  </h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                    {template?.purpose ||
                      "Select a template to preview the editor canvas."}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="docs-chip">
                    {template?.section_blueprint.length ?? 0} sections
                  </span>
                  <span className="docs-chip">{formatDocTypeLabel(startMode)}</span>
                  <span className="docs-chip">{formatDocTypeLabel(tonePreset)}</span>
                </div>
              </div>
            </div>

            <div className="bg-muted/10 px-4 py-5 md:px-6">
              <div className="docs-editor-page">
                <div className="flex items-center justify-between gap-3 border-b border-border/50 pb-5">
                  <div>
                    <p className="docs-eyebrow">Canvas preview</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">
                      {template?.label || "Untitled document"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      {creationMode === "sample" ? "AI-filled draft" : "Blank structure"}
                    </span>
                  </div>
                </div>

                <div className="mt-8 space-y-8">
                  {template?.section_blueprint.map((section, index) => (
                    <section
                      key={section.key}
                      className={index > 0 ? "border-t border-border/50 pt-8" : ""}
                    >
                      <p className="docs-eyebrow">
                        Section {String(index + 1).padStart(2, "0")}
                      </p>
                      <h3 className="mt-2 text-xl font-semibold text-foreground">
                        {section.label}
                      </h3>
                      <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">
                        {creationMode === "sample"
                          ? previewTextForSection(template, section.label)
                          : `This section opens empty so you can write ${section.label.toLowerCase()} directly on the canvas.`}
                      </p>
                    </section>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="docs-panel p-5">
            <div className="flex items-center gap-3">
              <Layers className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-foreground">Open mode</p>
                <p className="text-sm text-muted-foreground">
                  Choose whether the editor starts with AI-generated copy or a blank structure.
                </p>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              {CREATION_MODES.map((mode) => (
                <button
                  key={mode.key}
                  type="button"
                  onClick={() => setCreationMode(mode.key)}
                  className={cn(
                    "w-full rounded-xl border px-4 py-3 text-left transition-colors",
                    creationMode === mode.key
                      ? "border-border/70 bg-muted/10"
                      : "border-border/50 bg-background hover:bg-muted/10",
                  )}
                >
                  <span className="block text-sm font-medium text-foreground">
                    {mode.label}
                  </span>
                  <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                    {mode.description}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="docs-panel p-5">
            <p className="text-sm font-medium text-foreground">Tone preset</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Applied to AI-generated sample copy.
            </p>
            <Select
              value={tonePreset}
              className="docs-select mt-4"
              onChange={(event) =>
                setTonePreset(event.target.value as DocsTonePreset)
              }
            >
              {TONE_OPTIONS.map((tone) => (
                <SelectItem key={tone} value={tone}>
                  {formatDocTypeLabel(tone)}
                </SelectItem>
              ))}
            </Select>
          </div>

          <div className="docs-panel-muted p-5">
            <p className="text-sm font-medium text-foreground">Create</p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              The editor opens directly on the draft canvas. Structured details stay secondary.
            </p>
            <div className="mt-4 flex flex-col gap-3">
              <Button
                className="docs-button w-full justify-center"
                disabled={submitting !== null}
                onClick={() => void createDocument(creationMode)}
              >
                {submitting === creationMode
                  ? "Opening..."
                  : creationMode === "sample"
                    ? "Generate sample document"
                    : "Open blank template"}
              </Button>
              <Button
                variant="outline"
                className="docs-button-secondary w-full justify-center"
                disabled={submitting !== null}
                onClick={() =>
                  void createDocument(creationMode === "sample" ? "blank" : "sample")
                }
              >
                {creationMode === "sample"
                  ? "Open blank instead"
                  : "Generate sample instead"}
              </Button>
            </div>
            {error && <p className="mt-4 text-sm text-destructive">{error}</p>}
          </div>
        </aside>
      </div>
    </div>
  );
}
