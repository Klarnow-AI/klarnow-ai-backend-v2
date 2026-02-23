"use client";

import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { KanbanColumn } from "./kanban-column";
import type { Lead, PipelineStage } from "@/types/api-types";
import { PIPELINE_STAGES } from "@/types/api-types";

type KanbanBoardProps = {
  leads: Lead[];
  assigneeLabel?: string;
  onMoveLead: (leadId: string, pipelineStage: PipelineStage) => Promise<void>;
  onAddLead: (stage: PipelineStage) => void;
  onEditLead?: (lead: Lead) => void;
};

export function KanbanBoard({
  leads,
  assigneeLabel = "You",
  onMoveLead,
  onAddLead,
  onEditLead,
}: KanbanBoardProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const leadsByStage = PIPELINE_STAGES.reduce(
    (acc, stage) => {
      acc[stage] = leads.filter((l) => l.pipeline_stage === stage);
      return acc;
    },
    {} as Record<PipelineStage, Lead[]>
  );

  const totalByStage = PIPELINE_STAGES.reduce(
    (acc, stage) => {
      const stageLeads = leadsByStage[stage];
      acc[stage] = stageLeads.reduce(
        (sum, l) => sum + (l.deal_value != null ? Number(l.deal_value) : 0),
        0
      );
      return acc;
    },
    {} as Record<PipelineStage, number>
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const leadId = active.id as string;
    const overId = over.id;
    if (typeof overId !== "string") return;
    if (PIPELINE_STAGES.includes(overId as PipelineStage)) {
      const lead = leads.find((l) => l.id === leadId);
      if (lead && lead.pipeline_stage !== overId) {
        onMoveLead(leadId, overId as PipelineStage);
      }
    }
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {PIPELINE_STAGES.map((stage) => (
          <KanbanColumn
            key={stage}
            stage={stage}
            leads={leadsByStage[stage]}
            totalValue={totalByStage[stage]}
            assigneeLabel={assigneeLabel}
            onAddLead={onAddLead}
            onEditLead={onEditLead}
          />
        ))}
      </div>
    </DndContext>
  );
}
