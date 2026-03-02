"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { Check, Loader2, Pencil } from "@/components/icons";
import { Button } from "@/components/ui/button";
import type { Lead } from "@/types/api-types";

const QUALIFIED = "qualified";

export function createLeadColumns(handlers: {
  onQualify: (leadId: string) => void;
  onEdit: (lead: Lead) => void;
  qualifyingId: string | null;
}): ColumnDef<Lead>[] {
  return [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <div className="font-medium">{row.getValue("name")}</div>
      ),
    },
    {
      accessorKey: "email",
      header: "Email",
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.getValue("email") ?? "—"}
        </span>
      ),
    },
    {
      accessorKey: "phone",
      header: "Phone",
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.getValue("phone") ?? "—"}
        </span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
          {row.getValue("status")}
        </span>
      ),
    },
    {
      accessorKey: "pipeline_stage",
      header: "Stage",
      cell: ({ row }) => (
        <span className="rounded-full bg-muted/80 px-2 py-0.5 text-xs font-medium">
          {row.getValue("pipeline_stage")}
        </span>
      ),
    },
    {
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: ({ row }) => {
        const lead = row.original;
        return (
          <div className="flex items-center gap-2 justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlers.onEdit(lead)}
            >
              <Pencil className="h-4 w-4" size={16} />
            </Button>
            {lead.status !== QUALIFIED && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlers.onQualify(lead.id)}
                disabled={handlers.qualifyingId === lead.id}
              >
                {handlers.qualifyingId === lead.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" size={16} />
                ) : (
                  <>
                    <Check className="h-4 w-4" size={16} />
                    Qualify
                  </>
                )}
              </Button>
            )}
          </div>
        );
      },
    },
  ];
}
