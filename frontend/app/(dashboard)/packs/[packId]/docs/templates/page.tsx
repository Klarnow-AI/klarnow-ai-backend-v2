"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/page-loader";
import { docs as docsApi } from "@/api_requests/docs";
import { Layers, Sparkles } from "@/components/icons";
import type { DocsTemplate } from "@/types/api-types";
import { formatDocTypeLabel } from "../_components/docs-utils";

export default function DocsTemplatesPage() {
  const params = useParams();
  const packId = params.packId as string;
  const [templates, setTemplates] = useState<DocsTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    docsApi
      .listTemplates(packId)
      .then((items) => {
        if (!cancelled) setTemplates(items);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [packId]);

  const groupedTemplates = useMemo(() => {
    return templates.reduce<Record<string, DocsTemplate[]>>((groups, template) => {
      const key = template.category || "general";
      if (!groups[key]) groups[key] = [];
      groups[key].push(template);
      return groups;
    }, {});
  }, [templates]);

  if (loading) {
    return (
      <div className="docs-page-body">
        <div className="flex min-h-[50vh] items-center justify-center">
          <Spinner className="h-8 w-8" />
        </div>
      </div>
    );
  }

  return (
    <div className="docs-page-body docs-page-body-wide">
      <div className="max-w-3xl">
        <p className="docs-eyebrow">Template library</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
          Blueprint-driven document starts
        </h1>
        <p className="mt-3 text-sm leading-7 text-muted-foreground">
          Each template defines intake fields, section order, formatting rules,
          and generation guardrails. v0.1 ships fixed blueprints instead of
          user-authored templates.
        </p>
      </div>

      {Object.entries(groupedTemplates).map(([category, items]) => (
        <section key={category} className="space-y-4">
          <div className="flex items-center gap-3">
            <Layers className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="docs-eyebrow">{formatDocTypeLabel(category)}</p>
              <p className="text-base font-medium text-foreground">
                {items.length} template{items.length === 1 ? "" : "s"}
              </p>
            </div>
          </div>

          <div className="docs-panel overflow-hidden">
            {items.map((template, index) => (
              <div
                key={template.type}
                className={index < items.length - 1 ? "border-b border-border/50" : ""}
              >
                <div className="flex flex-col gap-4 px-5 py-5 xl:flex-row xl:items-start xl:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-base font-medium text-foreground">
                        {template.label}
                      </p>
                      <span className="docs-chip">
                        {template.section_blueprint.length} sections
                      </span>
                    </div>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
                      {template.purpose}
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {template.section_blueprint.map((section) => (
                        <span key={section.key} className="docs-chip">
                          {section.label}
                        </span>
                      ))}
                    </div>
                    {template.use_cases.length > 0 && (
                      <div className="mt-4 flex items-start gap-3">
                        <Sparkles className="mt-0.5 h-4 w-4 text-muted-foreground" />
                        <p className="text-sm leading-6 text-muted-foreground">
                          {template.use_cases.join(" · ")}
                        </p>
                      </div>
                    )}
                  </div>

                  <Link
                    href={`/packs/${packId}/docs/new?type=${encodeURIComponent(template.type)}&startMode=template`}
                  >
                    <Button className="docs-button">
                      Create {formatDocTypeLabel(template.type)}
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
