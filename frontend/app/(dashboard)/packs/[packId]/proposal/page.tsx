"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { FileCheck, Plus, Loader2 } from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { usePackGates } from "@/hooks/use-pack-gates";
import type {
  Proposal,
  ProposalCreateBody,
  ProposalUpdateBody,
} from "@/types/api-types";

export default function ProposalPage() {
  const params = useParams();
  const packId = params.packId as string;
  const { gates } = usePackGates(packId);
  const sectionUnlock = gates?.sections?.proposal;

  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formAmount, setFormAmount] = useState("");
  const [formCurrency, setFormCurrency] = useState("USD");
  const [formDueDate, setFormDueDate] = useState("");

  const cancelRef = useRef<(() => void) | undefined>(undefined);

  const fetchProposals = useCallback(async () => {
    if (!packId) return;
    cancelRef.current?.();
    let cancelled = false;
    cancelRef.current = () => {
      cancelled = true;
    };
    setLoading(true);
    setError(null);
    try {
      const res = await revenue.listProposals(packId);
      if (!cancelled) setProposals(res.items);
    } catch (e) {
      if (!cancelled)
        setError(e instanceof Error ? e.message : "Failed to load proposals");
    } finally {
      if (!cancelled) setLoading(false);
    }
  }, [packId]);

  useEffect(() => {
    fetchProposals();
    return () => {
      cancelRef.current?.();
    };
  }, [fetchProposals]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!packId || !formAmount.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const body: ProposalCreateBody = {
        amount: formAmount.trim(),
        currency: formCurrency,
        due_date: formDueDate.trim() || null,
      };
      await revenue.createProposal(packId, body);
      setFormAmount("");
      setFormCurrency("USD");
      setFormDueDate("");
      setCreateOpen(false);
      await fetchProposals();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create proposal");
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (
    proposalId: string,
    newStatus: string
  ) => {
    setEditingId(proposalId);
    setError(null);
    try {
      const body: ProposalUpdateBody = { status: newStatus };
      await revenue.updateProposal(proposalId, body);
      await fetchProposals();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update proposal");
    } finally {
      setEditingId(null);
    }
  };

  const canCreate = sectionUnlock?.unlocked ?? false;
  const gateMessage = sectionUnlock?.reason ?? null;

  return (
    <div className="p-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold tracking-tight">Proposal</h1>
        <p className="text-muted-foreground mt-1">
          Draft, send, and track proposals. Qualify a lead first to create one.
        </p>
      </motion.div>

      {error && (
        <div className="mb-4 rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {gateMessage && !canCreate && (
        <div className="mb-4 rounded-xl border border-amber-500/50 bg-amber-500/10 px-4 py-2 text-sm text-amber-700 dark:text-amber-400">
          {gateMessage}
        </div>
      )}

      <Card asMotion delay={0.1}>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-foreground">
              <FileCheck className="h-6 w-6" />
            </div>
            <div>
              <CardTitle>Proposals</CardTitle>
              <CardDescription>
                {loading
                  ? "Loading…"
                  : `${proposals.length} proposal${proposals.length === 1 ? "" : "s"}`}
              </CardDescription>
            </div>
          </div>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <Button
              variant="secondary"
              size="sm"
              disabled={!canCreate}
              onClick={() => setCreateOpen(true)}
            >
              <Plus className="h-4 w-4" />
              Create proposal
            </Button>
            {createOpen && (
              <DialogContent>
                <DialogHeader>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <DialogTitle>Create proposal</DialogTitle>
                      <DialogDescription>
                        Add amount and optional due date. You can update status
                        after creating.
                      </DialogDescription>
                    </div>
                    <DialogClose onClose={() => setCreateOpen(false)} />
                  </div>
                </DialogHeader>
                <form onSubmit={handleCreate}>
                  <DialogBody className="space-y-4">
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
                        value={formCurrency}
                        onValueChange={setFormCurrency}
                      >
                        <SelectTrigger id="currency" className="mt-1">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="USD">USD</SelectItem>
                          <SelectItem value="GBP">GBP</SelectItem>
                          <SelectItem value="EUR">EUR</SelectItem>
                          <SelectItem value="NGN">NGN</SelectItem>
                        </SelectContent>
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
                    <Button type="submit" disabled={submitting}>
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
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-muted-foreground">
              <Spinner className="h-5 w-5" />
              Loading proposals…
            </div>
          ) : proposals.length === 0 ? (
            <p className="py-6 text-sm text-muted-foreground">
              No proposals yet.
              {canCreate
                ? " Create a proposal to get started."
                : " Qualify a lead first to unlock creating proposals."}
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {proposals.map((proposal) => (
                <li
                  key={proposal.id}
                  className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0"
                >
                  <div>
                    <span className="font-medium">
                      {proposal.amount} {proposal.currency}
                    </span>
                    {proposal.due_date && (
                      <span className="ml-2 text-sm text-muted-foreground">
                        Due {proposal.due_date}
                      </span>
                    )}
                    <span
                      className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs font-medium"
                      title="Status"
                    >
                      {proposal.status}
                    </span>
                  </div>
                  {proposal.status === "draft" && (
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          handleStatusChange(proposal.id, "sent")
                        }
                        disabled={editingId === proposal.id}
                      >
                        {editingId === proposal.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          "Mark sent"
                        )}
                      </Button>
                    </div>
                  )}
                  {proposal.status === "sent" && (
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          handleStatusChange(proposal.id, "accepted")
                        }
                        disabled={editingId === proposal.id}
                      >
                        {editingId === proposal.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          "Accept"
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          handleStatusChange(proposal.id, "declined")
                        }
                        disabled={editingId === proposal.id}
                      >
                        Decline
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
