"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Users, Plus, Check, Loader2 } from "@/components/icons";
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
import { clients } from "@/api_requests/clients";
import type { Lead, LeadCreateBody } from "@/types/api-types";

const QUALIFIED = "qualified";

export default function LeadsPage() {
  const params = useParams();
  const packId = params.packId as string;
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [qualifyingId, setQualifyingId] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formPhone, setFormPhone] = useState("");

  const cancelRef = useRef<(() => void) | undefined>(undefined);

  const fetchLeads = useCallback(async () => {
    if (!packId) return;
    cancelRef.current?.();
    let cancelled = false;
    cancelRef.current = () => { cancelled = true; };
    setLoading(true);
    setError(null);
    try {
      const res = await clients.listLeads(packId);
      if (!cancelled) setLeads(res.items);
    } catch (e) {
      if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load leads");
    } finally {
      if (!cancelled) setLoading(false);
    }
  }, [packId]);

  useEffect(() => {
    fetchLeads();
    return () => { cancelRef.current?.(); };
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
      };
      await clients.createLead(body);
      setFormName("");
      setFormEmail("");
      setFormPhone("");
      setShowForm(false);
      await fetchLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create lead");
    } finally {
      setSubmitting(false);
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

  return (
    <div className="p-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
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

      <Card asMotion delay={0.1}>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-foreground">
              <Users className="h-6 w-6" />
            </div>
            <div>
              <CardTitle>Leads</CardTitle>
              <CardDescription>
                {loading
                  ? "Loading…"
                  : `${leads.length} lead${leads.length === 1 ? "" : "s"}`}
              </CardDescription>
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowForm((v) => !v)}
          >
            <Plus className="h-4 w-4" />
            Add lead
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {showForm && (
            <form
              onSubmit={handleCreate}
              className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-muted/30 p-4"
            >
              <div className="min-w-[160px]">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Name *
                </label>
                <Input
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Name"
                  required
                />
              </div>
              <div className="min-w-[180px]">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Email
                </label>
                <Input
                  type="email"
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                  placeholder="Email"
                />
              </div>
              <div className="min-w-[140px]">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Phone
                </label>
                <Input
                  value={formPhone}
                  onChange={(e) => setFormPhone(e.target.value)}
                  placeholder="Phone"
                />
              </div>
              <Button type="submit" disabled={submitting}>
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Save"
                )}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </Button>
            </form>
          )}

          {loading ? (
            <div className="flex items-center gap-2 py-6 text-muted-foreground">
              <Spinner className="h-5 w-5" />
              Loading leads…
            </div>
          ) : leads.length === 0 ? (
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
    </div>
  );
}
