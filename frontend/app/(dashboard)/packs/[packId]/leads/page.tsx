"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import {
  Plus,
  Check,
  Loader2,
  LayoutDashboard,
  GripVertical,
  ChevronDown,
} from "@/components/icons";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogBody,
  DialogClose,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { clients } from "@/api_requests/clients";
import type { Lead, LeadCreateBody, LeadUpdateBody, PipelineStage } from "@/types/api-types";
import { KanbanBoard } from "./_components/kanban-board";

const QUALIFIED = "qualified";

type ViewMode = "board" | "list";

export default function LeadsPage() {
  const params = useParams();
  const packId = params.packId as string;
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("board");
  const [showForm, setShowForm] = useState(false);
  const [defaultStage, setDefaultStage] = useState<PipelineStage | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [qualifyingId, setQualifyingId] = useState<string | null>(null);
  const [movingId, setMovingId] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formPhone, setFormPhone] = useState("");
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [editName, setEditName] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [editDueDate, setEditDueDate] = useState("");
  const [editDealValue, setEditDealValue] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  const cancelRef = useRef<(() => void) | undefined>(undefined);

  const fetchLeads = useCallback(async () => {
    if (!packId) return;
    cancelRef.current?.();
    let cancelled = false;
    cancelRef.current = () => {
      cancelled = true;
    };
    setLoading(true);
    setError(null);
    try {
      const res = await clients.listLeads(packId);
      if (!cancelled) {
        setLeads(
          res.items.map((l) => ({
            ...l,
            pipeline_stage: l.pipeline_stage ?? "contacted",
            due_date: l.due_date ?? null,
            deal_value: l.deal_value != null ? Number(l.deal_value) : null,
            assigned_user_id: l.assigned_user_id ?? null,
          }))
        );
      }
    } catch (e) {
      if (!cancelled)
        setError(e instanceof Error ? e.message : "Failed to load leads");
    } finally {
      if (!cancelled) setLoading(false);
    }
  }, [packId]);

  useEffect(() => {
    fetchLeads();
    return () => {
      cancelRef.current?.();
    };
  }, [fetchLeads]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!packId || !formName.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const body: LeadCreateBody = {
        pack_id: packId,
        name: formName.trim(),
        email: formEmail.trim() || null,
        phone: formPhone.trim() || null,
        pipeline_stage: defaultStage ?? undefined,
      };
      await clients.createLead(body);
      setFormName("");
      setFormEmail("");
      setFormPhone("");
      setShowForm(false);
      setDefaultStage(null);
      await fetchLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create lead");
    } finally {
      setSubmitting(false);
    }
  };

  const handleMoveLead = useCallback(
    async (leadId: string, pipelineStage: PipelineStage) => {
      setMovingId(leadId);
      setError(null);
      try {
        await clients.updateLead(leadId, { pipeline_stage: pipelineStage });
        setLeads((prev) =>
          prev.map((l) =>
            l.id === leadId ? { ...l, pipeline_stage: pipelineStage } : l
          )
        );
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to move lead");
      } finally {
        setMovingId(null);
      }
    },
    []
  );

  const handleAddLead = useCallback((stage: PipelineStage) => {
    setDefaultStage(stage);
    setShowForm(true);
  }, []);

  const openEdit = useCallback((lead: Lead) => {
    setEditingLead(lead);
    setEditName(lead.name);
    setEditSummary(lead.summary ?? "");
    setEditDueDate(lead.due_date ? lead.due_date.slice(0, 10) : "");
    setEditDealValue(lead.deal_value != null ? String(lead.deal_value) : "");
  }, []);

  const closeEdit = useCallback(() => {
    setEditingLead(null);
    setEditName("");
    setEditSummary("");
    setEditDueDate("");
    setEditDealValue("");
  }, []);

  const handleSaveEdit = async () => {
    if (!editingLead) return;
    setSavingEdit(true);
    setError(null);
    try {
      const body: LeadUpdateBody = {
        name: editName.trim() || undefined,
        summary: editSummary.trim() || null,
        due_date: editDueDate ? editDueDate : null,
        deal_value: editDealValue ? parseFloat(editDealValue) : null,
      };
      await clients.updateLead(editingLead.id, body);
      setLeads((prev) =>
        prev.map((l) =>
          l.id === editingLead.id
            ? {
                ...l,
                name: body.name ?? l.name,
                summary: body.summary ?? l.summary,
                due_date: body.due_date ?? l.due_date,
                deal_value: body.deal_value ?? l.deal_value,
              }
            : l
        )
      );
      closeEdit();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update lead");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleQualify = async (leadId: string) => {
    setQualifyingId(leadId);
    setError(null);
    try {
      await clients.qualifyLead(leadId);
      await fetchLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to qualify lead");
    } finally {
      setQualifyingId(null);
    }
  };

  const closedCount = leads.filter((l) => l.pipeline_stage === "closed").length;

  return (
    <div className="p-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h1 className="text-3xl font-bold tracking-tight">Leads</h1>
        <p className="text-muted-foreground mt-1">
          Add and qualify leads. Qualified leads unlock creating proposals.
        </p>
      </motion.div>

      {error && (
        <div className="mb-4 rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Header: stats, view toggles, filters, Add lead */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          {loading ? (
            <span className="flex items-center gap-2">
              <Spinner className="h-4 w-4" />
              Loading…
            </span>
          ) : (
            <>
              <span>
                Total: <strong className="text-foreground">{leads.length}</strong>{" "}
                Leads
              </span>
              <span>
                Closed:{" "}
                <strong className="text-foreground">{closedCount}</strong> Deals
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div
            className="inline-flex rounded-lg border border-border bg-muted/30 p-0.5"
            role="tablist"
            aria-label="View mode"
          >
            <button
              type="button"
              onClick={() => setViewMode("board")}
              className={`inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                viewMode === "board"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              aria-pressed={viewMode === "board"}
            >
              <LayoutDashboard className="h-4 w-4" size={16} />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("list")}
              className={`inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                viewMode === "list"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              aria-pressed={viewMode === "list"}
            >
              <GripVertical className="h-4 w-4" size={16} />
            </button>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5" disabled>
            <span>All leads</span>
            <ChevronDown className="h-4 w-4" size={16} />
          </Button>
          <Button variant="outline" size="sm" className="gap-1.5" disabled>
            Filter
          </Button>
          <Button
            size="sm"
            className="gap-1.5"
            onClick={() => {
              setDefaultStage(null);
              setShowForm(true);
            }}
          >
            <Plus className="h-4 w-4" size={16} />
            Add lead
          </Button>
        </div>
      </div>

      {/* Board or List view */}
      {loading ? (
        <div className="flex items-center gap-2 py-12 text-muted-foreground justify-center">
          <Spinner className="h-6 w-6" />
          Loading leads…
        </div>
      ) : viewMode === "board" ? (
        <KanbanBoard
          leads={leads}
          assigneeLabel="You"
          onMoveLead={handleMoveLead}
          onAddLead={handleAddLead}
          onEditLead={openEdit}
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Leads</CardTitle>
            <CardDescription>
              {leads.length} lead{leads.length === 1 ? "" : "s"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {leads.length === 0 ? (
              <p className="py-6 text-sm text-muted-foreground">
                No leads yet. Add a lead to get started.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {leads.map((lead) => (
                  <li
                    key={lead.id}
                    className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0"
                  >
                    <div>
                      <span className="font-medium">{lead.name}</span>
                      {lead.email && (
                        <span className="ml-2 text-sm text-muted-foreground">
                          {lead.email}
                        </span>
                      )}
                      {lead.phone && (
                        <span className="ml-2 text-sm text-muted-foreground">
                          {lead.phone}
                        </span>
                      )}
                      <span
                        className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs font-medium"
                        title="Status"
                      >
                        {lead.status}
                      </span>
                      <span
                        className="ml-2 rounded-full bg-muted/80 px-2 py-0.5 text-xs font-medium"
                        title="Stage"
                      >
                        {lead.pipeline_stage}
                      </span>
                    </div>
                    {lead.status !== QUALIFIED && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleQualify(lead.id)}
                        disabled={qualifyingId === lead.id}
                      >
                        {qualifyingId === lead.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <>
                            <Check className="h-4 w-4" />
                            Qualify
                          </>
                        )}
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {/* Add lead dialog */}
      <Dialog
        open={showForm}
        onOpenChange={(open) => {
          if (!open) {
            setShowForm(false);
            setDefaultStage(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {defaultStage ? `Add lead to ${defaultStage}` : "Add lead"}
            </DialogTitle>
            <DialogClose
              onClose={() => {
                setShowForm(false);
                setDefaultStage(null);
              }}
            />
          </DialogHeader>
          <DialogBody>
            <form
              onSubmit={handleCreate}
              className="space-y-4"
            >
              <div>
                <Label htmlFor="add-name">Name *</Label>
                <Input
                  id="add-name"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Name"
                  required
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="add-email">Email</Label>
                <Input
                  id="add-email"
                  type="email"
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                  placeholder="Email"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="add-phone">Phone</Label>
                <Input
                  id="add-phone"
                  value={formPhone}
                  onChange={(e) => setFormPhone(e.target.value)}
                  placeholder="Phone"
                  className="mt-1"
                />
              </div>
              {defaultStage && (
                <p className="text-sm text-muted-foreground">
                  Stage: <span className="font-medium capitalize text-foreground">{defaultStage}</span>
                </p>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowForm(false);
                    setDefaultStage(null);
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Save"
                  )}
                </Button>
              </div>
            </form>
          </DialogBody>
        </DialogContent>
      </Dialog>

      {/* Edit lead dialog */}
      <Dialog open={!!editingLead} onOpenChange={(open) => !open && closeEdit()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit lead</DialogTitle>
            <DialogClose onClose={closeEdit} />
          </DialogHeader>
          <DialogBody>
            <div className="space-y-4">
              <div>
                <Label htmlFor="edit-name">Name</Label>
                <Input
                  id="edit-name"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="edit-summary">Description / Summary</Label>
                <Textarea
                  id="edit-summary"
                  value={editSummary}
                  onChange={(e) => setEditSummary(e.target.value)}
                  rows={3}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="edit-due">Due date</Label>
                <Input
                  id="edit-due"
                  type="date"
                  value={editDueDate}
                  onChange={(e) => setEditDueDate(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="edit-value">Deal value ($)</Label>
                <Input
                  id="edit-value"
                  type="number"
                  min={0}
                  step={0.01}
                  value={editDealValue}
                  onChange={(e) => setEditDealValue(e.target.value)}
                  placeholder="0"
                  className="mt-1"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={closeEdit}>
                  Cancel
                </Button>
                <Button onClick={handleSaveEdit} disabled={savingEdit}>
                  {savingEdit ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
                </Button>
              </div>
            </div>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </div>
  );
}
