"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { Plus, Loader2, Bell, Receipt } from "@/components/icons";
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
import { packs as packsApi, type Pack } from "@/lib/api";
import { usePackGates } from "@/hooks/use-pack-gates";
import type {
  Invoice,
  InvoiceCreateBody,
  InvoiceUpdateBody,
} from "@/types/api-types";
import {
  createInvoiceColumns,
  formatInvoiceId,
} from "./_components/invoice-columns";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/empty-state";

type InvoiceWithPack = Invoice & { pack_name: string };

export default function InvoicesPage() {
  const searchParams = useSearchParams();
  const packFilter = searchParams.get("pack") ?? undefined;

  const [packs, setPacks] = useState<Pack[]>([]);
  const [invoices, setInvoices] = useState<InvoiceWithPack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createPackId, setCreatePackId] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [reminding, setReminding] = useState(false);
  const [formAmount, setFormAmount] = useState("");
  const [formCurrency, setFormCurrency] = useState("USD");
  const [formDueDate, setFormDueDate] = useState("");
  const [manageInvoice, setManageInvoice] = useState<InvoiceWithPack | null>(
    null,
  );
  const [connectStatus, setConnectStatus] = useState<{
    connected: boolean;
    onboarding_complete: boolean;
  } | null>(null);
  const [publishLoading, setPublishLoading] = useState(false);
  const [publishedLink, setPublishedLink] = useState<string | null>(null);

  const { gates: createPackGates } = usePackGates(createPackId || null);
  const sectionUnlock = createPackGates?.sections?.invoice;
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
      let items: InvoiceWithPack[] = [];
      if (packFilter) {
        const res = await revenue.listInvoices(packFilter);
        items = (res.items ?? []).map((p) => ({
          ...p,
          pack_name: packByName.get(p.pack_id) ?? p.pack_id,
        }));
      } else {
        const results = await Promise.all(
          packList.map((p) =>
            revenue.listInvoices(p.id).then((r) =>
              r.items.map((inv) => ({
                ...inv,
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
      if (!cancelled) setInvoices(items);
    } catch (e) {
      if (!cancelled)
        setError(e instanceof Error ? e.message : "Failed to load invoices");
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
    revenue
      .getConnectStatus()
      .then(setConnectStatus)
      .catch(() =>
        setConnectStatus({ connected: false, onboarding_complete: false }),
      );
  }, []);

  useEffect(() => {
    if (packs.length > 0 && !createPackId) setCreatePackId(packs[0].id);
  }, [packs, createPackId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createPackId || !formAmount.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const body: InvoiceCreateBody = {
        amount: formAmount.trim(),
        currency: formCurrency,
        due_date: formDueDate.trim() || null,
      };
      await revenue.createInvoice(createPackId, body);
      setFormAmount("");
      setFormCurrency("USD");
      setFormDueDate("");
      setCreateOpen(false);
      await fetchAll();
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
      await fetchAll();
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
      await fetchAll();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to send overdue reminders",
      );
    } finally {
      setReminding(false);
    }
  };

  const sentNotPaid = invoices.filter(
    (i) => i.status === "sent" || i.status === "overdue",
  ).length;

  if (loading) {
    return (
      <div className="flex min-h-[60vh] w-full max-w-[1400px] mx-auto items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Spinner className="h-6 w-6" />
          Loading invoices…
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1400px] mx-auto">
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
            href="/invoices"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Clear filter
          </Link>
        </div>
      )}

      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 shrink-0">
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
                  <Bell className="h-4 w-4" /> Remind overdue
                </>
              )}
            </Button>
          )}
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" /> New invoice
            </Button>
            {createOpen && (
              <DialogContent>
                <DialogHeader>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <DialogTitle>Create invoice</DialogTitle>
                      <DialogDescription>
                        Choose a pack, then add amount and optional due date.
                        The pack must have at least one accepted proposal.
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
                  <div className="flex justify-end gap-2 bg-border/20 px-6 py-4">
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
        </div>
      </div>

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

      <Card asMotion delay={0.1}>
        <CardContent className="p-0">
          {invoices.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={
                  <Receipt className="h-12 w-12 text-muted-foreground" />
                }
                title="No invoices yet"
                description="Create invoices from packs with accepted proposals. Get paid faster with Stripe payment links."
                actionLabel="New invoice"
                onAction={() => setCreateOpen(true)}
              />
            </div>
          ) : (
            <div className="p-4">
              <DataTable
                columns={createInvoiceColumns({
                  onManage: (inv) => setManageInvoice(inv),
                })}
                data={invoices}
                filterColumn="search"
                filterPlaceholder="Filter invoices..."
                showColumnVisibility
                initialState={{ columnVisibility: { search: false } }}
              />
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={!!manageInvoice}
        onOpenChange={(open) => {
          if (!open) {
            setManageInvoice(null);
            setPublishedLink(null);
          }
        }}
      >
        {manageInvoice && (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Manage invoice</DialogTitle>
              <DialogDescription>
                {formatInvoiceId(manageInvoice.id)} ·{" "}
                {manageInvoice.currency === "USD" && "$"}
                {Number.isNaN(Number(manageInvoice.amount))
                  ? manageInvoice.amount
                  : Number(manageInvoice.amount).toLocaleString()}
                {manageInvoice.currency !== "USD" &&
                  ` ${manageInvoice.currency}`}
              </DialogDescription>
              <DialogClose
                onClose={() => {
                  setManageInvoice(null);
                  setPublishedLink(null);
                }}
              />
            </DialogHeader>
            <DialogBody>
              <div className="flex flex-col gap-3">
                {manageInvoice.stripe_hosted_url ? (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Payment link ready. Share it with your client so they can
                      pay online.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(
                            manageInvoice.stripe_hosted_url!,
                          );
                        }}
                      >
                        Copy link
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          window.open(
                            manageInvoice.stripe_hosted_url!,
                            "_blank",
                          )
                        }
                      >
                        Open link
                      </Button>
                    </div>
                  </div>
                ) : connectStatus?.onboarding_complete ? (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Create a shareable payment link. Your client can pay by
                      card on Stripe.
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        if (!manageInvoice) return;
                        setPublishLoading(true);
                        setError(null);
                        try {
                          const res = await revenue.publishInvoice(
                            manageInvoice.id,
                          );
                          setPublishedLink(res.payment_link);
                          await fetchAll();
                          setManageInvoice((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  stripe_hosted_url: res.payment_link,
                                  stripe_invoice_id: res.stripe_invoice_id,
                                }
                              : null,
                          );
                        } catch (e) {
                          setError(
                            e instanceof Error
                              ? e.message
                              : "Failed to create payment link",
                          );
                        } finally {
                          setPublishLoading(false);
                        }
                      }}
                      disabled={publishLoading}
                    >
                      {publishLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Get payment link"
                      )}
                    </Button>
                    {publishedLink && (
                      <div className="flex flex-wrap gap-2 pt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            navigator.clipboard.writeText(publishedLink)
                          }
                        >
                          Copy link
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => window.open(publishedLink, "_blank")}
                        >
                          Open link
                        </Button>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    <Link
                      href="/settings"
                      className="text-primary hover:underline"
                    >
                      Connect Stripe
                    </Link>{" "}
                    in Settings to create payment links.
                  </p>
                )}
                <div className="flex flex-wrap gap-2 pt-2">
                  {manageInvoice.status === "draft" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        handleStatusChange(manageInvoice.id, "sent");
                        setManageInvoice(null);
                      }}
                      disabled={editingId === manageInvoice.id}
                    >
                      {editingId === manageInvoice.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Mark sent"
                      )}
                    </Button>
                  )}
                  {(manageInvoice.status === "sent" ||
                    manageInvoice.status === "overdue") && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        handleStatusChange(manageInvoice.id, "paid");
                        setManageInvoice(null);
                      }}
                      disabled={editingId === manageInvoice.id}
                    >
                      {editingId === manageInvoice.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Mark paid"
                      )}
                    </Button>
                  )}
                  {manageInvoice.status === "paid" && (
                    <p className="text-sm text-muted-foreground">
                      No actions available.
                    </p>
                  )}
                </div>
              </div>
            </DialogBody>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
