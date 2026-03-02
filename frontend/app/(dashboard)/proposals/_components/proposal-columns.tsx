"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import type { Proposal, ProposalStatus } from "@/types/api-types";
import { cn } from "@/lib/utils";

type ProposalWithPack = Proposal & { pack_name: string };

function formatProposalId(id: string): string {
  return id.replace(/-/g, "").slice(0, 9).toUpperCase();
}

function formatTableDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-GB", {
      weekday: "short",
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

function ProposalClientCell({ proposal }: { proposal: ProposalWithPack }) {
  const name = proposal.client_name ?? proposal.pack_name ?? "—";
  const initial = (name === "—" ? "?" : name).charAt(0).toUpperCase();
  const hue = name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;
  return (
    <div className="flex items-center gap-3">
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-medium text-white"
        style={{ backgroundColor: `hsl(${hue}, 60%, 45%)` }}
      >
        {initial}
      </div>
      <div className="min-w-0">
        <p className="truncate font-medium text-foreground">{name}</p>
      </div>
    </div>
  );
}

export function createProposalColumns(handlers: {
  onManage: (proposal: ProposalWithPack) => void;
}): ColumnDef<ProposalWithPack>[] {
  return [
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) =>
            table.toggleAllPageRowsSelected(!!value)
          }
          aria-label="Select all"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label={`Select ${formatProposalId(row.original.id)}`}
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      id: "search",
      accessorFn: (row) =>
        `${formatProposalId(row.id)} ${row.amount} ${row.pack_name ?? ""} ${row.client_name ?? ""}`.toLowerCase(),
      enableHiding: false,
      enableSorting: false,
    } as ColumnDef<ProposalWithPack>,
    {
      accessorKey: "id",
      header: "Proposal ID",
      cell: ({ row }) => (
        <span className="font-mono text-muted-foreground">
          {formatProposalId(row.getValue("id"))}
        </span>
      ),
    },
    {
      id: "client",
      accessorFn: (row) => row.client_name ?? row.pack_name ?? "—",
      header: "Client",
      cell: ({ row }) => (
        <ProposalClientCell proposal={row.original} />
      ),
    },
    {
      accessorKey: "amount",
      header: "Amount",
      cell: ({ row }) => {
        const p = row.original;
        return (
          <span className="font-medium">
            {p.currency === "USD" ? "$" : ""}
            {Number.isNaN(Number(p.amount))
              ? p.amount
              : Number(p.amount).toLocaleString()}
            {p.currency !== "USD" ? ` ${p.currency}` : ""}
          </span>
        );
      },
    },
    {
      accessorKey: "pack_name",
      header: "Product",
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.getValue("pack_name")}</span>
      ),
    },
    {
      id: "date",
      accessorFn: (row) => row.due_date ?? row.created_at,
      header: "Date",
      cell: ({ row }) => (
        <span className="text-muted-foreground whitespace-nowrap">
          {formatTableDate(
            row.original.due_date ?? row.original.created_at,
          )}
        </span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => {
        const status = row.getValue("status") as ProposalStatus;
        return (
          <span
            className={cn(
              "inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium",
              status === "accepted" &&
                "bg-green-500/20 text-green-700 dark:text-green-400",
              status === "declined" && "bg-destructive/20 text-destructive",
              status === "sent" &&
                "bg-amber-500/20 text-amber-700 dark:text-amber-400",
              status === "draft" && "bg-muted text-muted-foreground",
            )}
          >
            {status === "sent" ? "Pending" : status}
          </span>
        );
      },
    },
    {
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          className="bg-muted/50"
          onClick={() => handlers.onManage(row.original)}
        >
          Manage
        </Button>
      ),
      enableSorting: false,
      enableHiding: false,
    },
  ];
}
