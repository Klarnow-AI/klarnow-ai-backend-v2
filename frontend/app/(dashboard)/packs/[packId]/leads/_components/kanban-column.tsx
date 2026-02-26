"use client";

import { useDroppable } from "@dnd-kit/core";
import { KanbanCard } from "./kanban-card";
import { Button } from "@/components/ui/button";
import { Plus, MoreVertical } from "@/components/icons";
import { cn } from "@/lib/utils";
import type { Lead, PipelineStage } from "@/types/api-types";

const STAGE_LABEL: Record<PipelineStage, string> = {
  contacted: "Contacted",
  drafting: "Drafting",
  proposal: "Proposal",
  closed: "Closed",
};

type KanbanColumnProps = {
  stage: PipelineStage;
  leads: Lead[];
  totalValue: number;
  assigneeLabel?: string;
  onAddLead: (stage: PipelineStage) => void;
  onEditLead?: (lead: Lead) => void;
};

export function KanbanColumn({
  stage,
  leads,
  totalValue,
  assigneeLabel = "You",
  onAddLead,
  onEditLead,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: stage,
    data: { type: "column", stage },
  });

  const label = STAGE_LABEL[stage];
  const valueFormatted =
    totalValue > 0
      ? new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(totalValue)
      : "$0";

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex w-72 shrink-0 flex-col rounded-xl border border-border bg-muted/30",
        isOver && "ring-2 ring-primary/30 bg-muted/50",
      )}
    >
      <div className="flex items-center justify-between gap-2 p-3 border-b border-border">
        <div className="min-w-0">
          <h3 className="font-semibold text-foreground">{label}</h3>
          <p className="text-xs text-muted-foreground">
            {leads.length} Lead{leads.length === 1 ? "" : "s"} •{" "}
            {valueFormatted} Total
          </p>
        </div>
        <button
          type="button"
          className="p-1 rounded hover:bg-muted text-muted-foreground"
          aria-label="Column menu"
        >
          <MoreVertical className="h-4 w-4" size={16} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-[120px]">
        {leads.map((lead) => (
          <KanbanCard
            key={lead.id}
            lead={lead}
            assigneeLabel={assigneeLabel}
            onEdit={onEditLead}
          />
        ))}
      </div>
      <div className="p-2 border-t border-border">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start text-muted-foreground"
          onClick={() => onAddLead(stage)}
        >
          <Plus className="h-4 w-4" size={16} />
          Add
        </Button>
      </div>
    </div>
  );
}
