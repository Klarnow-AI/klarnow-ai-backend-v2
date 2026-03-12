"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/page-loader";
import { docs as docsApi } from "@/api_requests/docs";
import { FileText, Layers, Plus, Sparkles, Users } from "@/components/icons";
import type { DocsDocumentListItem, DocsHomeResponse } from "@/types/api-types";
import { formatDocTypeLabel } from "./_components/docs-utils";

const PRIMARY_ACTIONS = [
  {
    type: "proposal",
    label: "Create proposal",
    description: "Start from the proposal blueprint with reusable pricing and scope structure.",
    startMode: "template",
  },
  {
    type: "invoice",
    label: "Generate invoice",
    description: "Build a payment-ready invoice that can publish through the existing revenue flow.",
    startMode: "template",
  },
  {
    type: "company_profile",
    label: "Build company profile",
    description: "Turn pack and company context into a polished background document.",
    startMode: "template",
  },
  {
    type: "meeting_summary",
    label: "Turn notes into summary",
    description: "Paste notes or a transcript and let Docs map them into a structured summary.",
    startMode: "notes",
  },
] as const;

function RecentDocumentRow({
  packId,
  document,
}: {
  packId: string;
  document: DocsDocumentListItem;
}) {
  return (
    <div className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-base font-medium text-foreground">
            {document.title}
          </p>
          <span className="docs-chip">{formatDocTypeLabel(document.type)}</span>
          <span className="docs-chip">
            {document.status.replace(/_/g, " ")}
          </span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Updated{" "}
          {new Date(document.updated_at).toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </p>
      </div>
      <Link href={`/packs/${packId}/docs/${document.id}`}>
        <Button variant="outline" size="sm" className="docs-button-secondary">
          Open
        </Button>
      </Link>
    </div>
  );
}

export default function DocsHomePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const packId = params.packId as string;
  const typeFilter = searchParams.get("type");

  const [data, setData] = useState<DocsHomeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    docsApi
      .home(packId)
      .then((response) => {
        if (cancelled) return;
        setData(response);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load Docs");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [packId]);

  const recentDocuments = useMemo(() => {
    if (!data) return [];
    if (!typeFilter) return data.recent_documents;
    return data.recent_documents.filter((item) => item.type === typeFilter);
  }, [data, typeFilter]);

  const documentSummary = useMemo(() => {
    if (!data) {
      return {
        proposals: 0,
        invoices: 0,
        profiles: 0,
        summaries: 0,
        letters: 0,
      };
    }
    return {
      proposals: data.document_counts.proposal ?? 0,
      invoices: data.document_counts.invoice ?? 0,
      profiles: data.document_counts.company_profile ?? 0,
      summaries:
        (data.document_counts.meeting_summary ?? 0) +
        (data.document_counts.follow_up_summary ?? 0),
      letters:
        (data.document_counts.employment_letter ?? 0) +
        (data.document_counts.sponsorship_letter ?? 0),
    };
  }, [data]);

  if (loading) {
    return (
      <div className="docs-page-body">
        <div className="flex min-h-[50vh] items-center justify-center">
          <Spinner className="h-8 w-8" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="docs-page-body">
        <div className="docs-panel p-6">
          <p className="text-base font-medium text-foreground">Docs unavailable</p>
          <p className="mt-2 text-sm text-muted-foreground">
            {error || "Unable to load the Docs home."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="docs-page-body docs-page-body-wide">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_320px]">
        <div className="docs-panel px-6 py-8 md:px-8">
          <p className="docs-eyebrow">Pack-scoped workspace</p>
          <h1 className="mt-4 max-w-3xl text-3xl font-semibold tracking-tight text-foreground md:text-[2.5rem]">
            Build client-ready docs with context, not blank pages.
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-muted-foreground">
            Generate proposals, invoices, profiles, summaries, and formal
            letters directly from this pack. Docs keeps structure on the left,
            the draft in the center, and export-ready output at the end.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link href={`/packs/${packId}/docs/new`}>
              <Button className="docs-button">
                <Plus className="h-4 w-4" />
                New document
              </Button>
            </Link>
            <Link href={`/packs/${packId}/docs/templates`}>
              <Button
                variant="outline"
                className="docs-button-secondary"
              >
                <Layers className="h-4 w-4" />
                Browse templates
              </Button>
            </Link>
          </div>
        </div>

        <div className="docs-panel-muted p-5">
          <div className="flex items-start gap-3">
            <Users className="mt-0.5 h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium text-foreground">
                {data.company_data.business_name || "Company data not completed"}
              </p>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {data.company_data.tagline ||
                  "Add reusable business details, contact info, packages, and signatory defaults."}
              </p>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-border/50 bg-background px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Proposals
              </p>
              <p className="mt-2 text-2xl font-semibold text-foreground">
                {documentSummary.proposals}
              </p>
            </div>
            <div className="rounded-lg border border-border/50 bg-background px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Invoices
              </p>
              <p className="mt-2 text-2xl font-semibold text-foreground">
                {documentSummary.invoices}
              </p>
            </div>
            <div className="rounded-lg border border-border/50 bg-background px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Summaries
              </p>
              <p className="mt-2 text-2xl font-semibold text-foreground">
                {documentSummary.summaries}
              </p>
            </div>
            <div className="rounded-lg border border-border/50 bg-background px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Letters
              </p>
              <p className="mt-2 text-2xl font-semibold text-foreground">
                {documentSummary.letters}
              </p>
            </div>
          </div>
          <Link
            href={`/packs/${packId}/docs/company-data`}
            className="mt-5 inline-flex text-sm font-medium text-foreground transition-colors hover:text-muted-foreground"
          >
            Open company data
          </Link>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_340px]">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Sparkles className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-base font-medium text-foreground">
                Suggested for this sprint
              </p>
              <p className="text-sm text-muted-foreground">
                Suggestions adapt to leads, accepted docs, tasks, and missing
                company assets.
              </p>
            </div>
          </div>
          <div className="docs-panel overflow-hidden">
            {data.suggestions.length === 0 ? (
              <div className="px-5 py-8 text-sm text-muted-foreground">
                No suggestions yet. Start from a template or generate from notes.
              </div>
            ) : (
              data.suggestions.map((suggestion, index) => (
                <Link
                  key={`${suggestion.type}:${suggestion.priority}`}
                  href={suggestion.href}
                  className="block px-5 py-4 transition-colors hover:bg-muted/10"
                >
                  <div
                    className={
                      index < data.suggestions.length - 1
                        ? "border-b border-border/50 pb-4"
                        : ""
                    }
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-foreground">
                        {suggestion.label}
                      </p>
                      <span className="docs-chip">
                        {formatDocTypeLabel(suggestion.type)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {suggestion.reason}
                    </p>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-base font-medium text-foreground">
                Entry points
              </p>
              <p className="text-sm text-muted-foreground">
                Open a blank template or start from an AI-generated sample draft.
              </p>
            </div>
          </div>
          <div className="docs-panel overflow-hidden">
            {PRIMARY_ACTIONS.map((action, index) => (
              <div
                key={action.type}
                className="px-5 py-4"
              >
                <div
                  className={
                    index < PRIMARY_ACTIONS.length - 1
                      ? "border-b border-border/50 pb-4"
                      : ""
                  }
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {action.label}
                      </p>
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">
                        {action.description}
                      </p>
                    </div>
                    <Link
                      href={`/packs/${packId}/docs/new?type=${encodeURIComponent(action.type)}&startMode=${action.startMode}`}
                    >
                      <Button
                        variant="outline"
                        size="sm"
                        className="docs-button-secondary"
                      >
                        Start
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="docs-panel-muted p-4">
            <p className="text-sm font-medium text-foreground">
              Template library
            </p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {data.templates.length} blueprint
              {data.templates.length === 1 ? "" : "s"} available in this pack.
            </p>
            <Link
              href={`/packs/${packId}/docs/templates`}
              className="mt-3 inline-flex text-sm font-medium text-foreground transition-colors hover:text-muted-foreground"
            >
              Open templates
            </Link>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="docs-eyebrow">
              {typeFilter ? `${formatDocTypeLabel(typeFilter)} view` : "Recent"}
            </p>
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              {typeFilter
                ? `${formatDocTypeLabel(typeFilter)} documents`
                : "Recent documents"}
            </h2>
          </div>
          {typeFilter && (
            <Link
              href={`/packs/${packId}/docs`}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              Clear filter
            </Link>
          )}
        </div>
        <div className="docs-panel overflow-hidden">
          {recentDocuments.length === 0 ? (
            <div className="px-5 py-8 text-sm text-muted-foreground">
              No documents yet for this view.
            </div>
          ) : (
            recentDocuments.map((document, index) => (
              <div
                key={document.id}
                className={index < recentDocuments.length - 1 ? "border-b border-border/50" : ""}
              >
                <RecentDocumentRow packId={packId} document={document} />
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
