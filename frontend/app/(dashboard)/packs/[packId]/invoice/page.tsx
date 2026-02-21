"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Receipt, Plus, Loader2, Bell } from "@/components/icons";
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
  Invoice,
  InvoiceCreateBody,
  InvoiceUpdateBody,
} from "@/types/api-types";

export default function InvoicePage() {
  const params = useParams();
  const packId = params.packId as string;
  const { gates } = usePackGates(packId);
  const sectionUnlock = gates?.sections?.invoice;

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [reminding, setReminding] = useState(false);
  const [formAmount, setFormAmount] = useState("");
  const [formCurrency, setFormCurrency] = useState("USD");
  const [formDueDate, setFormDueDate] = useState("");

  const cancelRef = useRef<(() => void) | undefined>(undefined);

  const fetchInvoices = useCallback(async () => {
    if (!packId) return;
    cancelRef.current?.();
    let cancelled = false;
    cancelRef.current = () => {
      cancelled = true;
    };
    setLoading(true);
    setError(null);
    try {
      const res = await revenue.listInvoices(packId);
      if (!cancelled) setInvoices(res.items);
    } catch (e) {
      if (!cancelled)
        setError(e instanceof Error ? e.message : "Failed to load invoices");
    } finally {
      if (!cancelled) setLoading(false);
    }
  }, [packId]);

  useEffect(() => {
    fetchInvoices();
    return () => {
      cancelRef.current?.();
    };
  }, [fetchInvoices]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!packId || !formAmount.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const body: InvoiceCreateBody = {
        amount: formAmount.trim(),
        currency: formCurrency,
        due_date: formDueDate.trim() || null,
      };
      await revenue.createInvoice(packId, body);
      setFormAmount("");
      setFormCurrency("USD");
      setFormDueDate("");
      setCreateOpen(false);
      await fetchInvoices();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create invoice");
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (invoiceId: string, newStatus: string) => {
    setEditingId(invoiceId);
    setError(null);
    try {
      const body: InvoiceUpdateBody = { status: newStatus };
      await revenue.updateInvoice(invoiceId, body);
      await fetchInvoices();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update invoice");
    } finally {
      setEditingId(null);
    }
  };

  const handleRemindOverdue = async () => {
    setReminding(true);
    setError(null);
    try {
      await revenue.remindOverdue();
      await fetchInvoices();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to send overdue reminders"
      );
    } finally {
      setReminding(false);
    }
  };

  const canCreate = sectionUnlock?.unlocked ?? false;
  const gateMessage = sectionUnlock?.reason ?? null;
  const sentNotPaid = invoices.filter(
    (i) => i.status === "sent" || i.status === "overdue"
  ).length;

  return (
    <div className="p-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold tracking-tight">Invoice</h1>
        <p className="text-muted-foreground mt-1">
          Draft, send, and track payments. Get a proposal accepted first to
          create an invoice.
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
              <Receipt className="h-6 w-6" />
            </div>
            <div>
              <CardTitle>Invoices</CardTitle>
              <CardDescription>
                {loading
                  ? "Loading…"
                  : `${invoices.length} invoice${invoices.length === 1 ? "" : "s"}`}
              </CardDescription>
            </div>
          </div>
          <div className="flex gap-2">
            {sentNotPaid > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRemindOverdue}
                disabled={reminding}
              >
                {reminding ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Bell className="h-4 w-4" />
                    Remind overdue
                  </>
                )}
              </Button>
            )}
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
              <Button
                variant="secondary"
                size="sm"
                disabled={!canCreate}
                onClick={() => setCreateOpen(true)}
              >
                <Plus className="h-4 w-4" />
                Create invoice
              </Button>
              {createOpen && (
                <DialogContent>
                  <DialogHeader>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <DialogTitle>Create invoice</DialogTitle>
                        <DialogDescription>
                          Add amount and optional due date. You can update
                          status after creating.
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
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-muted-foreground">
              <Spinner className="h-5 w-5" />
              Loading invoices…
            </div>
          ) : invoices.length === 0 ? (
            <p className="py-6 text-sm text-muted-foreground">
              No invoices yet.
              {canCreate
                ? " Create an invoice to get started."
                : " Get a proposal accepted first to unlock creating invoices."}
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {invoices.map((invoice) => (
                <li
                  key={invoice.id}
                  className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0"
                >
                  <div>
                    <span className="font-medium">
                      {invoice.amount} {invoice.currency}
                    </span>
                    {invoice.due_date && (
                      <span className="ml-2 text-sm text-muted-foreground">
                        Due {invoice.due_date}
                      </span>
                    )}
                    <span
                      className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${
                        invoice.status === "paid"
                          ? "bg-green-500/20 text-green-700 dark:text-green-400"
                          : invoice.status === "overdue"
                            ? "bg-destructive/20 text-destructive"
                            : "bg-muted"
                      }`}
                      title="Status"
                    >
                      {invoice.status}
                    </span>
                  </div>
                  {invoice.status === "draft" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStatusChange(invoice.id, "sent")}
                      disabled={editingId === invoice.id}
                    >
                      {editingId === invoice.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Mark sent"
                      )}
                    </Button>
                  )}
                  {(invoice.status === "sent" ||
                    invoice.status === "overdue") && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStatusChange(invoice.id, "paid")}
                      disabled={editingId === invoice.id}
                    >
                      {editingId === invoice.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Mark paid"
                      )}
                    </Button>
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
