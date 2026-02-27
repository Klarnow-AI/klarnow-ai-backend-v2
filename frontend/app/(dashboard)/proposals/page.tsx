"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Plus,
  Loader2,
  LayoutDashboard,
  GripVertical,
} from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectItem } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogBody,
  DialogClose,
} from "@/components/ui/dialog";
import { revenue } from "@/api_requests/revenue";
import { clients } from "@/api_requests/clients";
import { packs as packsApi, type Pack } from "@/lib/api";
import { usePackGates } from "@/hooks/use-pack-gates";
import type {
  Proposal,
  ProposalCreateBody,
  ProposalUpdateBody,
  ProposalStatus,
  Lead,
  ProposalGeneratedContent,
} from "@/types/api-types";
import { ProposalKanbanBoard } from "./_components/proposal-kanban-board";
import { cn } from "@/lib/utils";

type ProposalWithPack = Proposal & { pack_name: string };
type ViewMode = "table" | "kanban";

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

export default function ProposalsPage() {
  const searchParams = useSearchParams();
  const packFilter = searchParams.get("pack") ?? undefined;

  const [packs, setPacks] = useState<Pack[]>([]);
  const [proposals, setProposals] = useState<ProposalWithPack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createPackId, setCreatePackId] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formAmount, setFormAmount] = useState("");
  const [formCurrency, setFormCurrency] = useState("USD");
  const [formDueDate, setFormDueDate] = useState("");
  const [formContent, setFormContent] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [createClientId, setCreateClientId] = useState<string | null>(null);
  const [qualifiedLeads, setQualifiedLeads] = useState<Lead[]>([]);
  const [loadingLeads, setLoadingLeads] = useState(false);
  const [generatingDraft, setGeneratingDraft] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("kanban");
  const [editingProposal, setEditingProposal] = useState<Proposal | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const { gates: createPackGates } = usePackGates(createPackId || null);
  const sectionUnlock = createPackGates?.sections?.proposal;
  const canCreateForSelectedPack = sectionUnlock?.unlocked ?? false;
  const gateMessage = sectionUnlock?.reason ?? null;

  const cancelRef = useRef<(() => void) | undefined>(undefined);

  const fetchAll = useCallback(async () => {
    cancelRef.current?.();
    let cancelled = false;
    cancelRef.current = () => {
      cancelled = true;
    };
    setLoading(true);
    setError(null);
    try {
      const packsRes = await packsApi.list();
      if (cancelled) return;
      const packList = packsRes.items;
      setPacks(packList);
      const packByName = new Map(packList.map((p) => [p.id, p.name]));
      let items: ProposalWithPack[] = [];
      if (packFilter) {
        const res = await revenue.listProposals(packFilter);
        items = (res.items ?? []).map((p) => ({
          ...p,
          pack_name: packByName.get(p.pack_id) ?? p.pack_id,
        }));
      } else {
        const results = await Promise.all(
          packList.map((p) =>
            revenue.listProposals(p.id).then((r) =>
              r.items.map((prop) => ({
                ...prop,
                pack_name: p.name,
              })),
            ),
          ),
        );
        items = results
          .flat()
          .sort(
            (a, b) =>
              new Date(b.updated_at).getTime() -
              new Date(a.updated_at).getTime(),
          );
      }
      if (!cancelled) setProposals(items);
    } catch (e) {
      if (!cancelled)
        setError(e instanceof Error ? e.message : "Failed to load proposals");
    } finally {
      if (!cancelled) setLoading(false);
    }
  }, [packFilter]);

  useEffect(() => {
    fetchAll();
    return () => {
      cancelRef.current?.();
    };
  }, [fetchAll]);

  useEffect(() => {
    if (packs.length > 0 && !createPackId) setCreatePackId(packs[0].id);
  }, [packs, createPackId]);

  useEffect(() => {
    if (!createOpen || !createPackId) {
      setQualifiedLeads([]);
      return;
    }
    setCreateClientId(null);
    let cancelled = false;
    setLoadingLeads(true);
    clients
      .listLeads(createPackId, true)
      .then((res) => {
        if (!cancelled) setQualifiedLeads(res.items ?? []);
      })
      .catch(() => {
        if (!cancelled) setQualifiedLeads([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingLeads(false);
      });
    return () => {
      cancelled = true;
    };
  }, [createOpen, createPackId]);

  const handleGenerateDraft = async () => {
    if (!createPackId) return;
    setGeneratingDraft(true);
    setError(null);
    try {
      const clientIdForApi = createClientId
        ? (qualifiedLeads.find((l) => l.id === createClientId)?.client_id ??
          createClientId)
        : null;
      const res = await revenue.generateProposalDraft(
        createPackId,
        clientIdForApi ?? undefined,
      );
      setFormAmount(res.suggested_amount ?? "");
      setFormDueDate(res.suggested_due_date ?? "");
      setFormContent(res.content as Record<string, unknown>);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate draft");
    } finally {
      setGeneratingDraft(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createPackId || !formAmount.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const clientIdForApi = createClientId
        ? (qualifiedLeads.find((l) => l.id === createClientId)?.client_id ??
          null)
        : null;
      const body: ProposalCreateBody = {
        amount: formAmount.trim(),
        currency: formCurrency,
        due_date: formDueDate.trim() || null,
        content: formContent ?? undefined,
        client_id: clientIdForApi ?? undefined,
      };
      await revenue.createProposal(createPackId, body);
      setFormAmount("");
      setFormCurrency("USD");
      setFormDueDate("");
      setFormContent(null);
      setCreateClientId(null);
      setCreateOpen(false);
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create proposal");
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (proposalId: string, newStatus: string) => {
    setEditingId(proposalId);
    setError(null);
    try {
      const body: ProposalUpdateBody = { status: newStatus };
      await revenue.updateProposal(proposalId, body);
      setEditingProposal(null);
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update proposal");
    } finally {
      setEditingId(null);
    }
  };

  const handleMoveProposal = useCallback(
    async (proposalId: string, status: ProposalStatus) => {
      setEditingId(proposalId);
      setError(null);
      try {
        await revenue.updateProposal(proposalId, { status });
        setProposals((prev) =>
          prev.map((p) => (p.id === proposalId ? { ...p, status } : p)),
        );
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to update proposal");
      } finally {
        setEditingId(null);
      }
    },
    [],
  );

  const filteredProposals = useMemo(() => {
    if (!searchQuery.trim()) return proposals;
    const q = searchQuery.trim().toLowerCase();
    return proposals.filter(
      (p) =>
        formatProposalId(p.id).toLowerCase().includes(q) ||
        p.amount.toLowerCase().includes(q) ||
        p.pack_name?.toLowerCase().includes(q) ||
        p.client_name?.toLowerCase().includes(q),
    );
  }, [proposals, searchQuery]);

  const allSelected =
    filteredProposals.length > 0 &&
    filteredProposals.every((p) => selectedIds.has(p.id));
  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filteredProposals.forEach((p) => next.delete(p.id));
        return next;
      });
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filteredProposals.forEach((p) => next.add(p.id));
        return next;
      });
    }
  };

  return (
    <div
      className={
        viewMode === "kanban" ? "w-full" : "w-full max-w-[1400px] mx-auto"
      }
    >
      {packFilter && packs.length > 0 && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            Filtered by pack:
          </span>
          <Link
            href={`/packs/${packFilter}`}
            className="text-sm font-medium text-primary hover:underline"
          >
            {packs.find((p) => p.id === packFilter)?.name ?? packFilter}
          </Link>
          <Link
            href="/proposals"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Clear filter
          </Link>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {createOpen && gateMessage && !canCreateForSelectedPack && (
        <div className="mb-4 rounded-xl border border-amber-500/50 bg-amber-500/10 px-4 py-2 text-sm text-amber-700 dark:text-amber-400">
          {gateMessage}
        </div>
      )}

      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1 min-w-0 max-w-sm">
          <Input
            type="text"
            placeholder="Search proposal..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-10"
          />
          <Button variant="outline" size="sm" className="shrink-0 h-10">
            Default Filter
          </Button>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <div
            className="inline-flex rounded-lg border border-border bg-muted/30 p-0.5"
            role="tablist"
            aria-label="View mode"
          >
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${viewMode === "table" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              aria-pressed={viewMode === "table"}
            >
              <GripVertical className="h-4 w-4" size={16} /> Table
            </button>
            <button
              type="button"
              onClick={() => setViewMode("kanban")}
              className={`inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${viewMode === "kanban" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              aria-pressed={viewMode === "kanban"}
            >
              <LayoutDashboard className="h-4 w-4" size={16} /> Kanban
            </button>
          </div>
          <Button
            size="sm"
            className="gap-1.5"
            onClick={() => setCreateOpen(true)}
          >
            <Plus className="h-4 w-4" size={16} /> New Proposal
          </Button>
        </div>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        {createOpen && (
          <DialogContent>
            <DialogHeader>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <DialogTitle>Create proposal</DialogTitle>
                  <DialogDescription>
                    Choose a pack, then add amount and optional due date. The
                    pack must have at least one qualified lead.
                  </DialogDescription>
                </div>
                <DialogClose onClose={() => setCreateOpen(false)} />
              </div>
            </DialogHeader>
            <form onSubmit={handleCreate}>
              <DialogBody className="space-y-4">
                <div>
                  <Label htmlFor="create-pack">Pack</Label>
                  <Select
                    id="create-pack"
                    value={createPackId}
                    onChange={(e) => setCreatePackId(e.target.value)}
                    className="mt-1"
                  >
                    {packs.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </Select>
                </div>
                <div>
                  <Label htmlFor="create-client">
                    Client / lead (optional)
                  </Label>
                  <Select
                    id="create-client"
                    value={createClientId ?? ""}
                    onChange={(e) => setCreateClientId(e.target.value || null)}
                    className="mt-1"
                  >
                    <SelectItem value="">No client</SelectItem>
                    {loadingLeads ? (
                      <SelectItem value="_loading" disabled>
                        Loading…
                      </SelectItem>
                    ) : (
                      qualifiedLeads.map((lead) => (
                        <SelectItem key={lead.id} value={lead.id}>
                          {lead.name}
                          {lead.client_id ? ` (client)` : ""}
                        </SelectItem>
                      ))
                    )}
                  </Select>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleGenerateDraft}
                    disabled={
                      !createPackId ||
                      generatingDraft ||
                      !canCreateForSelectedPack
                    }
                  >
                    {generatingDraft ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Generate draft"
                    )}
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    AI-generated content and suggested amount
                  </span>
                </div>
                {formContent && (
                  <div className="rounded-md border border-border bg-muted/30 p-3 text-sm space-y-2">
                    {(formContent as ProposalGeneratedContent).description && (
                      <p className="text-foreground">
                        {(formContent as ProposalGeneratedContent).description}
                      </p>
                    )}
                    {Array.isArray(
                      (formContent as ProposalGeneratedContent).line_items,
                    ) &&
                      (formContent as ProposalGeneratedContent).line_items!
                        .length > 0 && (
                        <ul className="list-disc list-inside text-muted-foreground">
                          {(
                            formContent as ProposalGeneratedContent
                          ).line_items!.map((item, i) => (
                            <li key={i}>
                              {item.label}: {item.description}
                            </li>
                          ))}
                        </ul>
                      )}
                  </div>
                )}
                <div>
                  <Label htmlFor="amount">Amount *</Label>
                  <Input
                    id="amount"
                    type="text"
                    value={formAmount}
                    onChange={(e) => setFormAmount(e.target.value)}
                    placeholder="e.g. 1500.00"
                    required
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="currency">Currency</Label>
                  <Select
                    id="currency"
                    value={formCurrency}
                    onChange={(e) => setFormCurrency(e.target.value)}
                    className="mt-1"
                  >
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="GBP">GBP</SelectItem>
                    <SelectItem value="EUR">EUR</SelectItem>
                    <SelectItem value="NGN">NGN</SelectItem>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="due_date">Due date</Label>
                  <Input
                    id="due_date"
                    type="date"
                    value={formDueDate}
                    onChange={(e) => setFormDueDate(e.target.value)}
                    className="mt-1"
                  />
                </div>
              </DialogBody>
              <div className="flex justify-end gap-2 border-t border-border px-6 py-4">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setCreateOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={submitting || !canCreateForSelectedPack}
                >
                  {submitting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Create"
                  )}
                </Button>
              </div>
            </form>
          </DialogContent>
        )}
      </Dialog>

      {/* Edit proposal / status actions dialog */}
      <Dialog
        open={!!editingProposal}
        onOpenChange={(open) => !open && setEditingProposal(null)}
      >
        {editingProposal && (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Update proposal</DialogTitle>
              <DialogDescription>
                {editingProposal.amount} {editingProposal.currency}
                {editingProposal.client_name &&
                  ` • ${editingProposal.client_name}`}
              </DialogDescription>
              <DialogClose onClose={() => setEditingProposal(null)} />
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    revenue
                      .downloadProposalPdf(editingProposal.id)
                      .catch((e) =>
                        setError(
                          e instanceof Error ? e.message : "Download failed",
                        ),
                      );
                  }}
                >
                  Download PDF
                </Button>
                {editingProposal.status === "draft" && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      handleStatusChange(editingProposal.id, "sent");
                    }}
                    disabled={editingId === editingProposal.id}
                  >
                    {editingId === editingProposal.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Mark sent"
                    )}
                  </Button>
                )}
                {editingProposal.status === "sent" && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        handleStatusChange(editingProposal.id, "accepted")
                      }
                      disabled={editingId === editingProposal.id}
                    >
                      {editingId === editingProposal.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Accept"
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        handleStatusChange(editingProposal.id, "declined")
                      }
                      disabled={editingId === editingProposal.id}
                    >
                      Decline
                    </Button>
                  </>
                )}
                {(editingProposal.status === "accepted" ||
                  editingProposal.status === "declined") && (
                  <p className="text-sm text-muted-foreground">
                    No further actions.
                  </p>
                )}
              </div>
            </DialogBody>
          </DialogContent>
        )}
      </Dialog>

      {loading ? (
        <div className="flex items-center gap-2 py-12 justify-center text-muted-foreground">
          <Spinner className="h-6 w-6" /> Loading proposals…
        </div>
      ) : viewMode === "kanban" ? (
        proposals.length === 0 ? (
          <Card>
            <CardContent className="py-12">
              <p className="text-center text-sm text-muted-foreground">
                No proposals yet. Create one using a pack that has at least one
                qualified lead.
              </p>
            </CardContent>
          </Card>
        ) : (
          <ProposalKanbanBoard
            proposals={proposals}
            onMoveProposal={handleMoveProposal}
            onEditProposal={(p) => setEditingProposal(p)}
            onDownloadPdf={(p) =>
              revenue
                .downloadProposalPdf(p.id)
                .catch((e) =>
                  setError(e instanceof Error ? e.message : "Download failed"),
                )
            }
            onAddProposal={() => setCreateOpen(true)}
          />
        )
      ) : (
        <Card asMotion delay={0.1}>
          <CardContent className="p-0">
            {proposals.length === 0 ? (
              <p className="py-12 px-6 text-center text-sm text-muted-foreground">
                No proposals yet. Create one using a pack that has at least one
                qualified lead.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-10">
                        <Checkbox
                          checked={allSelected}
                          onCheckedChange={toggleSelectAll}
                          aria-label="Select all"
                        />
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Proposal ID
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Client
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Amount
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Product
                      </TableHead>
                      <TableHead className="whitespace-nowrap">Date</TableHead>
                      <TableHead className="whitespace-nowrap">
                        Status
                      </TableHead>
                      <TableHead className="text-right w-24"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredProposals.map((proposal) => (
                      <TableRow key={proposal.id}>
                        <TableCell>
                          <Checkbox
                            checked={selectedIds.has(proposal.id)}
                            onCheckedChange={(checked) => {
                              setSelectedIds((prev) => {
                                const next = new Set(prev);
                                if (checked) next.add(proposal.id);
                                else next.delete(proposal.id);
                                return next;
                              });
                            }}
                            aria-label={`Select ${formatProposalId(proposal.id)}`}
                          />
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          {formatProposalId(proposal.id)}
                        </TableCell>
                        <TableCell>
                          <ProposalClientCell proposal={proposal} />
                        </TableCell>
                        <TableCell className="font-medium">
                          {proposal.currency === "USD" ? "$" : ""}
                          {Number.isNaN(Number(proposal.amount))
                            ? proposal.amount
                            : Number(proposal.amount).toLocaleString()}
                          {proposal.currency !== "USD"
                            ? ` ${proposal.currency}`
                            : ""}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {proposal.pack_name}
                        </TableCell>
                        <TableCell className="text-muted-foreground whitespace-nowrap">
                          {formatTableDate(
                            proposal.due_date ?? proposal.created_at,
                          )}
                        </TableCell>
                        <TableCell>
                          <span
                            className={cn(
                              "inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium",
                              proposal.status === "accepted" &&
                                "bg-green-500/20 text-green-700 dark:text-green-400",
                              proposal.status === "declined" &&
                                "bg-destructive/20 text-destructive",
                              proposal.status === "sent" &&
                                "bg-amber-500/20 text-amber-700 dark:text-amber-400",
                              proposal.status === "draft" &&
                                "bg-muted text-muted-foreground",
                            )}
                          >
                            {proposal.status === "sent"
                              ? "Pending"
                              : proposal.status}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            className="bg-muted/50"
                            onClick={() => setEditingProposal(proposal)}
                          >
                            Manage
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
