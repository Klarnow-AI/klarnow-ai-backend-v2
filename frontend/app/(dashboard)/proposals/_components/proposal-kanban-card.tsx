"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Calendar, Pencil, Check, X, Download } from "@/components/icons";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Proposal } from "@/types/api-types";

function formatDate(dateStr: string | null): string | null {
  if (!dateStr) return null;
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return null;
  }
}

function dueInDays(dueDate: string | null): number | null {
  if (!dueDate) return null;
  try {
    const due = new Date(dueDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    due.setHours(0, 0, 0, 0);
    const diff = Math.ceil(
      (due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
    );
    return diff;
  } catch {
    return null;
  }
}

function formatAmount(amount: string, currency: string): string {
  const num = parseFloat(amount);
  if (Number.isNaN(num)) return `${amount} ${currency}`;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency || "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num);
}

type ProposalKanbanCardProps = {
  proposal: Proposal;
  onEdit?: (proposal: Proposal) => void;
  onDownloadPdf?: (proposal: Proposal) => void;
};

export function ProposalKanbanCard({
  proposal,
  onEdit,
  onDownloadPdf,
}: ProposalKanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({
      id: proposal.id,
      data: { proposal, type: "card" },
    });

  const style = transform
    ? { transform: CSS.Translate.toString(transform) }
    : undefined;

  const createdStr = formatDate(proposal.created_at);
  const dueDays = dueInDays(proposal.due_date);
  const dueLabel =
    dueDays !== null
      ? dueDays < 0
        ? `Overdue ${Math.abs(dueDays)} days ago`
        : dueDays === 0
          ? "Due today"
          : `Due in ${dueDays} days`
      : null;
  const isUrgent = dueDays !== null && dueDays >= 0 && dueDays <= 3;

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className={cn(
        "cursor-grab active:cursor-grabbing rounded-xl border border-border bg-card p-4 shadow-sm transition-shadow",
        "hover:shadow-md",
        isDragging && "opacity-90 shadow-lg ring-2 ring-primary/20",
      )}
      {...attributes}
      {...listeners}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h4 className="font-medium text-foreground truncate">
            {formatAmount(proposal.amount, proposal.currency)}
          </h4>
          <p className="mt-0.5 text-xs text-muted-foreground truncate">
            {proposal.client_name ??
              (proposal as Proposal & { pack_name?: string }).pack_name ??
              "—"}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {onDownloadPdf && (
            <button
              type="button"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={(e) => {
                e.stopPropagation();
                onDownloadPdf(proposal);
              }}
              className="rounded p-1 text-muted-foreground hover:bg-muted"
              aria-label="Download PDF"
            >
              <Download className="h-3.5 w-3.5" size={14} />
            </button>
          )}
          {onEdit && (
            <button
              type="button"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={(e) => {
                e.stopPropagation();
                onEdit(proposal);
              }}
              className="rounded p-1 text-muted-foreground hover:bg-muted"
              aria-label="Edit proposal"
            >
              <Pencil className="h-3.5 w-3.5" size={14} />
            </button>
          )}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        {createdStr && (
          <>
            <Calendar className="h-3.5 w-3.5 shrink-0" size={14} />
            <span>{createdStr}</span>
            {dueLabel && (
              <>
                <span>→</span>
                <span
                  className={cn(isUrgent && "font-medium text-destructive")}
                >
                  {dueLabel}
                </span>
              </>
            )}
          </>
        )}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
          {formatAmount(proposal.amount, proposal.currency)}
        </span>
        {(proposal.status === "accepted" || proposal.status === "declined") && (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
              proposal.status === "accepted"
                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                : "bg-destructive/10 text-destructive",
            )}
          >
            {proposal.status === "accepted" ? (
              <>
                <Check className="h-3 w-3" size={12} />
                Accepted
              </>
            ) : (
              <>
                <X className="h-3 w-3" size={12} />
                Declined
              </>
            )}
          </span>
        )}
      </div>
    </Card>
  );
}
