"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { docs as docsApi } from "@/api_requests/docs";
import { Download, Receipt } from "@/components/icons";
import type { DocsDocumentListItem } from "@/types/api-types";
import { formatDocTypeLabel } from "../_components/docs-utils";

export default function DocsExportsPage() {
  const params = useParams();
  const packId = params.packId as string;
  const [documents, setDocuments] = useState<DocsDocumentListItem[]>([]);

  useEffect(() => {
    docsApi.listDocuments(packId).then((response) => setDocuments(response.items));
  }, [packId]);

  return (
    <div className="docs-page-body docs-page-body-wide">
      <div className="max-w-3xl">
        <p className="docs-eyebrow">Exports</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
          PDF-first document output
        </h1>
        <p className="mt-3 text-sm leading-7 text-muted-foreground">
          Every document exports as PDF. Invoice rows can also publish into the
          existing payment-link flow from this view.
        </p>
      </div>

      <div className="docs-panel overflow-hidden">
        {documents.length === 0 ? (
          <div className="px-5 py-8 text-sm text-muted-foreground">
            No documents available yet.
          </div>
        ) : (
          documents.map((document, index) => (
            <div
              key={document.id}
              className={index < documents.length - 1 ? "border-b border-border/50" : ""}
            >
              <div className="flex flex-col gap-4 px-5 py-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-base font-medium text-foreground">
                      {document.title}
                    </p>
                    <span className="docs-chip">
                      {formatDocTypeLabel(document.type)}
                    </span>
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
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    className="docs-button-secondary"
                    onClick={() => void docsApi.downloadPdf(packId, document.id)}
                  >
                    <Download className="h-4 w-4" />
                    Download PDF
                  </Button>
                  {document.type === "invoice" && (
                    <Button
                      className="docs-button"
                      onClick={() => void docsApi.publishInvoice(packId, document.id)}
                    >
                      <Receipt className="h-4 w-4" />
                      Publish invoice
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
