"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import {
  Mail,
  Phone,
  FileText,
  Receipt,
  Check,
  Calendar,
  Pencil,
} from "@/components/icons";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Lead } from "@/types/api-types";

const STAGE_ICON: Record<string, React.ComponentType<{ className?: string; size?: number }>> = {
  contacted: Mail,
  drafting: FileText,
  proposal: Receipt,
  closed: Check,
};

function getLeadIcon(lead: Lead) {
  if (lead.pipeline_stage === "closed") return Check;
  if (lead.source === "conversion_page" || lead.email) return Mail;
  if (lead.phone) return Phone;
  return STAGE_ICON[lead.pipeline_stage] ?? FileText;
}

function formatDueDate(dueDate: string | null): string | null {
  if (!dueDate) return null;
  try {
    const d = new Date(dueDate);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return null;
  }
}

type KanbanCardProps = {
  lead: Lead;
  assigneeLabel?: string;
  onEdit?: (lead: Lead) => void;
};

export function KanbanCard({ lead, assigneeLabel = "You", onEdit }: KanbanCardProps) {
  const Icon = getLeadIcon(lead);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    isDragging,
  } = useDraggable({
    id: lead.id,
    data: { lead, type: "card" },
  });

  const style = transform
    ? { transform: CSS.Translate.toString(transform) }
    : undefined;

  const description = lead.summary?.split("\n")[0]?.slice(0, 80) ?? "";
  const dueStr = formatDueDate(lead.due_date);

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className={cn(
        "cursor-grab active:cursor-grabbing rounded-xl border border-border bg-card p-4 shadow-sm transition-shadow",
        "hover:shadow-md",
        isDragging && "opacity-90 shadow-lg ring-2 ring-primary/20",
        lead.urgency === "high" && "border-l-4 border-l-destructive"
      )}
      {...attributes}
      {...listeners}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h4 className="font-medium text-foreground truncate">{lead.name}</h4>
          {description && (
            <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
              {description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {onEdit && (
            <button
              type="button"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={(e) => {
                e.stopPropagation();
                onEdit(lead);
              }}
              className="p-1 rounded hover:bg-muted text-muted-foreground"
              aria-label="Edit lead"
            >
              <Pencil className="h-3.5 w-3.5" size={14} />
            </button>
          )}
          <Icon className="h-4 w-4 text-muted-foreground" size={16} />
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        {lead.email && (
          <a
            href={`mailto:${lead.email}`}
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 min-w-0 truncate text-muted-foreground hover:text-foreground hover:underline"
            title={lead.email}
          >
            <Mail className="h-3.5 w-3.5 shrink-0" size={14} />
            <span className="truncate">{lead.email}</span>
          </a>
        )}
        {lead.phone && (
          <a
            href={`tel:${lead.phone}`}
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 min-w-0 truncate text-muted-foreground hover:text-foreground hover:underline"
            title={lead.phone}
          >
            <Phone className="h-3.5 w-3.5 shrink-0" size={14} />
            <span className="truncate">{lead.phone}</span>
          </a>
        )}
        <div className="flex items-center gap-1 shrink-0 min-w-0">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary font-medium">
            {assigneeLabel.slice(0, 1).toUpperCase()}
          </span>
          <span className="truncate">{assigneeLabel}</span>
        </div>
        {dueStr && (
          <>
            <Calendar className="h-3.5 w-3.5 shrink-0" size={14} />
            <span>{dueStr}</span>
          </>
        )}
      </div>
    </Card>
  );
}
