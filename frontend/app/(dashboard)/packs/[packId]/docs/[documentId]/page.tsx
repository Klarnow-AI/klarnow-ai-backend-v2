"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectItem } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { docs as docsApi } from "@/api_requests/docs";
import {
  Download,
  FileText,
  Receipt,
  RotateCcw,
  Sparkles,
} from "@/components/icons";
import { cn } from "@/lib/utils";
import type {
  DocsDocument,
  DocsDocumentStatus,
  DocsTemplate,
  DocsTonePreset,
} from "@/types/api-types";
import { DocsFieldForm } from "../_components/docs-field-form";
import { formatDocTypeLabel } from "../_components/docs-utils";

const TABS = [
  { key: "draft", label: "Draft" },
  { key: "overview", label: "Properties" },
  { key: "inputs", label: "Details" },
  { key: "export", label: "Export" },
] as const;

const STATUS_OPTIONS: DocsDocumentStatus[] = [
  "draft",
  "generated",
  "in_review",
  "ready_to_send",
  "sent",
  "accepted",
  "paid",
  "archived",
];

const SECTION_ACTIONS = [
  { key: "rewrite", label: "Rewrite" },
  { key: "shorten", label: "Shorten" },
  { key: "expand", label: "Expand" },
  { key: "more_formal", label: "More formal" },
  { key: "more_persuasive", label: "More persuasive" },
  { key: "bullets", label: "To bullets" },
  { key: "add_next_steps", label: "Add next steps" },
  { key: "regenerate", label: "Regenerate" },
] as const;

function TabButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex h-9 items-center rounded-md px-3 text-sm transition-colors",
        active
          ? "bg-foreground text-background"
          : "border border-border/60 bg-background text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
}

function sectionPlaceholder(label: string): string {
  return `Start writing ${label.toLowerCase()} here, or use an AI action to generate a sample version.`;
}

export default function DocumentWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const packId = params.packId as string;
  const documentId = params.documentId as string;

  const [document, setDocument] = useState<DocsDocument | null>(null);
  const [templates, setTemplates] = useState<DocsTemplate[]>([]);
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["key"]>("draft");
  const [inputs, setInputs] = useState<Record<string, unknown>>({});
  const [sections, setSections] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<null | "draft" | "inputs" | "overview">(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = async () => {
    const [doc, templateList] = await Promise.all([
      docsApi.getDocument(packId, documentId),
      docsApi.listTemplates(packId),
    ]);
    setDocument(doc);
    setTemplates(templateList);
    setInputs(doc.inputs_json ?? {});
    setSections(
      Object.fromEntries(doc.sections.map((section) => [section.id, section.content])),
    );
  };

  useEffect(() => {
    void refresh();
  }, [packId, documentId]);

  const template = useMemo(
    () => templates.find((item) => item.type === document?.type) ?? null,
    [document?.type, templates],
  );

  const allFields = useMemo(
    () => (template ? [...template.required_fields, ...template.optional_fields] : []),
    [template],
  );

  const isBlankDraft = useMemo(() => {
    if (!document) return true;
    return document.sections.every((section) => !(sections[section.id] ?? section.content).trim());
  }, [document, sections]);

  const saveInputs = async () => {
    if (!document) return;
    setSaving("inputs");
    setMessage(null);
    try {
      const updated = await docsApi.updateDocument(packId, document.id, {
        title: document.title,
        status: document.status,
        tone_preset: document.tone_preset,
        inputs_json: inputs,
      });
      setDocument(updated);
      setMessage("Details saved.");
    } finally {
      setSaving(null);
    }
  };

  const saveDraft = async () => {
    if (!document) return;
    setSaving("draft");
    setMessage(null);
    try {
      const updated = await docsApi.updateDocument(packId, document.id, {
        sections: document.sections.map((section) => ({
          id: section.id,
          content: sections[section.id] ?? section.content,
        })),
      });
      setDocument(updated);
      setSections(
        Object.fromEntries(updated.sections.map((section) => [section.id, section.content])),
      );
      setMessage("Draft saved.");
    } finally {
      setSaving(null);
    }
  };

  const runSectionAction = async (
    sectionId: string,
    action: (typeof SECTION_ACTIONS)[number]["key"],
  ) => {
    const updated = await docsApi.applySectionAction(packId, documentId, sectionId, action);
    setDocument(updated);
    setSections(
      Object.fromEntries(updated.sections.map((section) => [section.id, section.content])),
    );
    setMessage("Section updated.");
  };

  const regenerateDocument = async () => {
    const updated = await docsApi.generateDocument(packId, documentId);
    setDocument(updated);
    setInputs(updated.inputs_json ?? {});
    setSections(
      Object.fromEntries(updated.sections.map((section) => [section.id, section.content])),
    );
    setMessage("Sample draft generated.");
  };

  const updateOverview = async (patch: {
    title?: string;
    status?: DocsDocumentStatus;
    tone_preset?: DocsTonePreset;
  }) => {
    if (!document) return;
    setSaving("overview");
    setMessage(null);
    try {
      const updated = await docsApi.updateDocument(packId, document.id, patch);
      setDocument(updated);
      setMessage("Properties saved.");
    } finally {
      setSaving(null);
    }
  };

  if (!document) {
    return (
      <div className="docs-page-body">
        <p className="text-sm text-muted-foreground">Loading document…</p>
      </div>
    );
  }

  const missingFields =
    (document.source_context_json?.missing_fields as string[] | undefined) ?? [];
  const warnings =
    (document.source_context_json?.warnings as string[] | undefined) ?? [];
  const paymentLink =
    (document.export_meta_json?.payment_link as string | undefined) ?? null;

  return (
    <div className="docs-page-body docs-page-body-wide">
      <div className="border-b border-border/60 pb-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <p className="docs-eyebrow">{formatDocTypeLabel(document.type)}</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground md:text-[2.5rem]">
              {document.title}
            </h1>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="docs-chip">{document.status.replace(/_/g, " ")}</span>
              <span className="docs-chip">
                Tone: {formatDocTypeLabel(document.tone_preset)}
              </span>
              <span className="docs-chip">{document.sections.length} blocks</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="docs-button-secondary"
              onClick={() => void regenerateDocument()}
            >
              <Sparkles className="h-4 w-4" />
              Generate sample
            </Button>
            <Button
              variant="outline"
              className="docs-button-secondary"
              onClick={() => void saveDraft()}
              disabled={saving === "draft"}
            >
              {saving === "draft" ? "Saving..." : "Save draft"}
            </Button>
            <Button
              variant="outline"
              className="docs-button-secondary"
              onClick={() => void docsApi.downloadPdf(packId, document.id)}
            >
              <Download className="h-4 w-4" />
              PDF
            </Button>
            <Button
              variant="outline"
              className="docs-button-secondary"
              onClick={() => router.push(`/packs/${packId}/docs`)}
            >
              Back
            </Button>
          </div>
        </div>

        {message && <p className="mt-4 text-sm text-muted-foreground">{message}</p>}

        {(missingFields.length > 0 || warnings.length > 0) && (
          <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-4 text-sm text-amber-100">
            {missingFields.length > 0 && (
              <p>Missing fields: {missingFields.join(", ")}</p>
            )}
            {warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-2">
          {TABS.map((tab) => (
            <TabButton
              key={tab.key}
              active={activeTab === tab.key}
              label={tab.label}
              onClick={() => setActiveTab(tab.key)}
            />
          ))}
        </div>
      </div>

      {activeTab === "draft" && (
        <div className="grid gap-6 xl:grid-cols-[220px_minmax(0,1fr)]">
          <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
            <div className="docs-panel-muted p-4">
              <p className="docs-eyebrow">Outline</p>
              <div className="mt-3 space-y-1">
                {document.sections.map((section, index) => (
                  <a
                    key={section.id}
                    href={`#section-${section.id}`}
                    className="flex items-center gap-3 rounded-lg px-2 py-2 text-sm text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
                  >
                    <span className="text-xs">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="truncate">{section.section_label}</span>
                  </a>
                ))}
              </div>
            </div>

            <div className="docs-panel p-4">
              <p className="text-sm font-medium text-foreground">Canvas mode</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                This view is the editable document itself. Use AI actions per
                section or generate a complete sample draft from the top bar.
              </p>
            </div>
          </aside>

          <div className="space-y-5">
            <div className="docs-editor-page">
              <div className="flex flex-col gap-3 border-b border-border/50 pb-6 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="docs-eyebrow">Document canvas</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">
                    {document.title}
                  </p>
                </div>
                {document.type === "invoice" && (
                  <Button
                    className="docs-button"
                    onClick={async () => {
                      const response = await docsApi.publishInvoice(packId, document.id);
                      setDocument((current) =>
                        current
                          ? {
                              ...current,
                              export_meta_json: {
                                ...(current.export_meta_json ?? {}),
                                payment_link: response.payment_link,
                                stripe_invoice_id: response.stripe_invoice_id,
                              },
                            }
                          : current,
                      );
                      setMessage("Invoice published.");
                    }}
                  >
                    <Receipt className="h-4 w-4" />
                    Publish invoice
                  </Button>
                )}
              </div>

              {isBlankDraft && (
                <div className="mt-6 rounded-xl border border-dashed border-border/60 bg-muted/10 px-5 py-5">
                  <p className="text-sm font-medium text-foreground">
                    Blank template opened
                  </p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">
                    Start writing directly in the sections below, or generate a
                    sample draft to get AI-created starter content.
                  </p>
                </div>
              )}

              <div className="mt-8 space-y-10">
                {document.sections.map((section, index) => (
                  <section
                    key={section.id}
                    id={`section-${section.id}`}
                    className={index > 0 ? "border-t border-border/50 pt-10" : ""}
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p className="docs-eyebrow">
                          Section {String(index + 1).padStart(2, "0")}
                        </p>
                        <h2 className="mt-2 text-2xl font-semibold text-foreground">
                          {section.section_label}
                        </h2>
                      </div>
                    </div>

                    <Textarea
                      rows={Math.max(6, Math.ceil((sections[section.id] ?? section.content).length / 120))}
                      className="docs-editor-textarea mt-4"
                      value={sections[section.id] ?? section.content}
                      placeholder={sectionPlaceholder(section.section_label)}
                      onChange={(event) =>
                        setSections((current) => ({
                          ...current,
                          [section.id]: event.target.value,
                        }))
                      }
                    />

                    <div className="mt-4 flex flex-wrap gap-2">
                      {SECTION_ACTIONS.map((action) => (
                        <Button
                          key={action.key}
                          variant="outline"
                          size="sm"
                          className="docs-button-secondary h-8 px-3 text-xs"
                          onClick={() => void runSectionAction(section.id, action.key)}
                        >
                          {action.label}
                        </Button>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "overview" && (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
          <div className="docs-panel p-6">
            <div className="grid gap-6">
              <div className="grid gap-4 lg:grid-cols-3">
                <div className="grid gap-2">
                  <Label htmlFor="title" className="text-sm font-medium">
                    Title
                  </Label>
                  <Input
                    id="title"
                    className="docs-input"
                    value={document.title}
                    onChange={(event) =>
                      setDocument((current) =>
                        current ? { ...current, title: event.target.value } : current,
                      )
                    }
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="status" className="text-sm font-medium">
                    Status
                  </Label>
                  <Select
                    id="status"
                    value={document.status}
                    className="docs-select"
                    onChange={(event) =>
                      setDocument((current) =>
                        current
                          ? {
                              ...current,
                              status: event.target.value as DocsDocumentStatus,
                            }
                          : current,
                      )
                    }
                  >
                    {STATUS_OPTIONS.map((status) => (
                      <SelectItem key={status} value={status}>
                        {status.replace(/_/g, " ")}
                      </SelectItem>
                    ))}
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="tone" className="text-sm font-medium">
                    Tone
                  </Label>
                  <Select
                    id="tone"
                    value={document.tone_preset}
                    className="docs-select"
                    onChange={(event) =>
                      setDocument((current) =>
                        current
                          ? {
                              ...current,
                              tone_preset: event.target.value as DocsTonePreset,
                            }
                          : current,
                      )
                    }
                  >
                    {["formal", "professional", "persuasive", "concise", "warm"].map((tone) => (
                      <SelectItem key={tone} value={tone}>
                        {formatDocTypeLabel(tone)}
                      </SelectItem>
                    ))}
                  </Select>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  className="docs-button"
                  disabled={saving === "overview"}
                  onClick={() =>
                    void updateOverview({
                      title: document.title,
                      status: document.status,
                      tone_preset: document.tone_preset,
                    })
                  }
                >
                  {saving === "overview" ? "Saving..." : "Save properties"}
                </Button>
              </div>
            </div>
          </div>

          <aside className="docs-panel-muted p-5">
            <div className="flex items-start gap-3">
              <FileText className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  Secondary properties
                </p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Metadata lives here, but the draft canvas remains the primary
                  surface for day-to-day editing.
                </p>
              </div>
            </div>
          </aside>
        </div>
      )}

      {activeTab === "inputs" && (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
          <div className="docs-panel p-6">
            <DocsFieldForm
              fields={allFields}
              values={inputs}
              onChange={(key, value) => setInputs((current) => ({ ...current, [key]: value }))}
            />
            <div className="mt-6 flex flex-wrap gap-3">
              <Button
                onClick={() => void saveInputs()}
                disabled={saving === "inputs"}
                className="docs-button"
              >
                {saving === "inputs" ? "Saving..." : "Save details"}
              </Button>
              <Button
                variant="outline"
                onClick={() => void regenerateDocument()}
                className="docs-button-secondary"
              >
                Regenerate from details
              </Button>
            </div>
          </div>

          <aside className="docs-panel-muted p-5">
            <div className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  Advanced details
                </p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Use this only when you need structured data to sharpen the
                  generated draft. It is no longer the primary creation flow.
                </p>
              </div>
            </div>
          </aside>
        </div>
      )}

      {activeTab === "export" && (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
          <div className="docs-panel p-6">
            <p className="text-base font-medium text-foreground">Export actions</p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              PDF is the default output for every document. Invoice drafts can
              also publish a payment link from this view.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button
                className="docs-button"
                onClick={() => void docsApi.downloadPdf(packId, document.id)}
              >
                <Download className="h-4 w-4" />
                Download PDF
              </Button>
              {document.type === "invoice" && (
                <Button
                  variant="outline"
                  className="docs-button-secondary"
                  onClick={async () => {
                    const response = await docsApi.publishInvoice(packId, document.id);
                    setDocument((current) =>
                      current
                        ? {
                            ...current,
                            export_meta_json: {
                              ...(current.export_meta_json ?? {}),
                              payment_link: response.payment_link,
                              stripe_invoice_id: response.stripe_invoice_id,
                            },
                          }
                        : current,
                    );
                    setMessage("Invoice published.");
                  }}
                >
                  <Receipt className="h-4 w-4" />
                  Publish invoice
                </Button>
              )}
            </div>
          </div>

          <aside className="space-y-4">
            {paymentLink && (
              <div className="docs-panel-muted p-5">
                <p className="text-sm font-medium text-foreground">
                  Payment link
                </p>
                <a
                  href={paymentLink}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 block break-all text-sm text-primary hover:underline"
                >
                  {paymentLink}
                </a>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
