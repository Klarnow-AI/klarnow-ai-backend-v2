"use client";

import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { ProposalKanbanColumn } from "./proposal-kanban-column";
import type { Proposal, ProposalStatus } from "@/types/api-types";
import { PROPOSAL_KANBAN_STAGES } from "@/types/api-types";

type ProposalKanbanBoardProps = {
  proposals: Proposal[];
  onMoveProposal: (proposalId: string, status: ProposalStatus) => Promise<void>;
  onEditProposal?: (proposal: Proposal) => void;
  onDownloadPdf?: (proposal: Proposal) => void;
  onAddProposal?: () => void;
};

export function ProposalKanbanBoard({
  proposals,
  onMoveProposal,
  onEditProposal,
  onDownloadPdf,
  onAddProposal,
}: ProposalKanbanBoardProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
  );

  const proposalsByStage = PROPOSAL_KANBAN_STAGES.reduce(
    (acc, stage) => {
      acc[stage] = proposals.filter((p) => p.status === stage);
      return acc;
    },
    {} as Record<ProposalStatus, Proposal[]>,
  );

  const totalByStage = PROPOSAL_KANBAN_STAGES.reduce(
    (acc, stage) => {
      const stageProposals = proposalsByStage[stage];
      acc[stage] = stageProposals.reduce(
        (sum, p) => sum + (parseFloat(p.amount) || 0),
        0,
      );
      return acc;
    },
    {} as Record<ProposalStatus, number>,
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const proposalId = active.id as string;
    const overId = over.id;
    if (typeof overId !== "string") return;
    if (PROPOSAL_KANBAN_STAGES.includes(overId as ProposalStatus)) {
      const proposal = proposals.find((p) => p.id === proposalId);
      if (proposal && proposal.status !== overId) {
        onMoveProposal(proposalId, overId as ProposalStatus);
      }
    }
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {PROPOSAL_KANBAN_STAGES.map((stage) => (
          <ProposalKanbanColumn
            key={stage}
            stage={stage}
            proposals={proposalsByStage[stage]}
            totalValue={totalByStage[stage]}
            onEditProposal={onEditProposal}
            onDownloadPdf={onDownloadPdf}
            onAddProposal={stage === "draft" ? onAddProposal : undefined}
          />
        ))}
      </div>
    </DndContext>
  );
}
