"use client";

import { useDroppable } from "@dnd-kit/core";
import { ProposalKanbanCard } from "./proposal-kanban-card";
import { Button } from "@/components/ui/button";
import { Plus } from "@/components/icons";
import { cn } from "@/lib/utils";
import type { Proposal, ProposalStatus } from "@/types/api-types";

const STAGE_LABEL: Record<ProposalStatus, string> = {
  draft: "In Progress",
  sent: "Follow Up",
  accepted: "Accepted",
  declined: "Declined",
};

const STAGE_HEADER_CLASS: Record<ProposalStatus, string> = {
  draft: "bg-muted",
  sent: "bg-amber-100 dark:bg-amber-950/50",
  accepted: "bg-emerald-100 dark:bg-emerald-950/50",
  declined: "bg-muted",
};

type ProposalKanbanColumnProps = {
  stage: ProposalStatus;
  proposals: Proposal[];
  totalValue: number;
  onEditProposal?: (proposal: Proposal) => void;
  onDownloadPdf?: (proposal: Proposal) => void;
  onAddProposal?: () => void;
};

export function ProposalKanbanColumn({
  stage,
  proposals,
  totalValue,
  onEditProposal,
  onDownloadPdf,
  onAddProposal,
}: ProposalKanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: stage,
    data: { type: "column", stage },
  });

  const label = STAGE_LABEL[stage];
  const headerClass = STAGE_HEADER_CLASS[stage];
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
      <div
        className={cn(
          "flex items-center justify-between gap-2 rounded-t-xl border-b border-border p-3",
          headerClass,
        )}
      >
        <div className="min-w-0">
          <h3 className="font-semibold text-foreground">{label}</h3>
          <p className="text-xs text-muted-foreground">
            {proposals.length} Proposal{proposals.length === 1 ? "" : "s"} •{" "}
            {valueFormatted} Total
          </p>
        </div>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-2 min-h-[120px]">
        {proposals.map((proposal) => (
          <ProposalKanbanCard
            key={proposal.id}
            proposal={proposal}
            onEdit={onEditProposal}
            onDownloadPdf={onDownloadPdf}
          />
        ))}
      </div>
      {onAddProposal && (
        <div className="border-t border-border p-2">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-muted-foreground"
            onClick={onAddProposal}
          >
            <Plus className="h-4 w-4" size={16} />
            Add
          </Button>
        </div>
      )}
    </div>
  );
}
