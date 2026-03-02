"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Plus, Loader2, ChevronDown, Target } from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  PIPELINE_STAGES,
  type Lead,
  type LeadCreateBody,
  type LeadUpdateBody,
  type PipelineStage,
} from "@/types/api-types";
import { createLeadColumns } from "./_components/lead-columns";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function LeadsPage() {
  const params = useParams();
  const packId = params.packId as string;
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [defaultStage, setDefaultStage] = useState<PipelineStage | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [qualifyingId, setQualifyingId] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formPhone, setFormPhone] = useState("");
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [editName, setEditName] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [editDueDate, setEditDueDate] = useState("");
  const [editDealValue, setEditDealValue] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [stageFilter, setStageFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const cancelRef = useRef<(() => void) | undefined>(undefined);

  const filteredLeads = leads.filter((lead) => {
    if (stageFilter !== "all" && lead.pipeline_stage !== stageFilter)
      return false;
    if (statusFilter === "qualified" && lead.status !== "qualified")
      return false;
    if (statusFilter === "not_qualified" && lead.status === "qualified")
      return false;
    return true;
  });

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
          })),
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
            : l,
        ),
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

  if (loading) {
    return (
      <div className="flex min-h-[60vh] w-full items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Spinner className="h-6 w-6" />
          Loading leads…
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h1 className="text-3xl  font-[600] tracking-tight">Leads</h1>
        <p className="text-muted-foreground mt-1">
          Add and qualify leads. Qualified leads unlock creating proposals.
        </p>
      </motion.div>

      {error && (
        <div className="mb-4 rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Header: Add lead */}
      <div className="mb-6 flex flex-wrap items-center justify-end gap-4">
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

      {/* Table view */}
      <Card>
        <CardContent className="pt-10">
          {leads.length === 0 ? (
            <EmptyState
              icon={<Target className="h-12 w-12 text-muted-foreground" />}
              title="No leads yet"
              description="Add contacts to track and qualify. Qualified leads unlock creating proposals."
              actionLabel="Add lead"
              onAction={() => {
                setDefaultStage(null);
                setShowForm(true);
              }}
            />
          ) : (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="gap-1.5">
                      <span>
                        {stageFilter === "all"
                          ? "All leads"
                          : stageFilter.charAt(0).toUpperCase() +
                            stageFilter.slice(1)}
                      </span>
                      <ChevronDown className="h-4 w-4" size={16} />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuRadioGroup
                      value={stageFilter}
                      onValueChange={setStageFilter}
                    >
                      <DropdownMenuRadioItem value="all">
                        All leads
                      </DropdownMenuRadioItem>
                      {PIPELINE_STAGES.map((stage) => (
                        <DropdownMenuRadioItem
                          key={stage}
                          value={stage}
                          className="capitalize"
                        >
                          {stage}
                        </DropdownMenuRadioItem>
                      ))}
                    </DropdownMenuRadioGroup>
                  </DropdownMenuContent>
                </DropdownMenu>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="gap-1.5">
                      <span>
                        {statusFilter === "all"
                          ? "Filter"
                          : statusFilter === "qualified"
                            ? "Qualified"
                            : "Not qualified"}
                      </span>
                      <ChevronDown className="h-4 w-4" size={16} />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuRadioGroup
                      value={statusFilter}
                      onValueChange={setStatusFilter}
                    >
                      <DropdownMenuRadioItem value="all">
                        All statuses
                      </DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="qualified">
                        Qualified
                      </DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="not_qualified">
                        Not qualified
                      </DropdownMenuRadioItem>
                    </DropdownMenuRadioGroup>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <DataTable
                columns={createLeadColumns({
                  onQualify: handleQualify,
                  onEdit: openEdit,
                  qualifyingId,
                })}
                data={filteredLeads}
                filterColumn="name"
                filterPlaceholder="Filter by name..."
                showColumnVisibility
                showSelectionCount={false}
              />
            </div>
          )}
        </CardContent>
      </Card>

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
            <form onSubmit={handleCreate} className="space-y-4">
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
                  Stage:{" "}
                  <span className="font-medium capitalize text-foreground">
                    {defaultStage}
                  </span>
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
      <Dialog
        open={!!editingLead}
        onOpenChange={(open) => !open && closeEdit()}
      >
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
                  {savingEdit ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Save"
                  )}
                </Button>
              </div>
            </div>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </div>
  );
}
