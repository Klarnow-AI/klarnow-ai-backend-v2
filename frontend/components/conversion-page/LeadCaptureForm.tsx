"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { publicApi } from "@/api_requests/public";

export function LeadCaptureForm({
  packId,
  enabled = true,
  headline = "Get in touch",
  subheadline = "Leave your details and we’ll reach out.",
}: {
  packId: string;
  enabled?: boolean;
  headline?: string;
  subheadline?: string;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [summary, setSummary] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    if (!enabled) return false;
    if (!name.trim()) return false;
    if (!email.trim() && !phone.trim()) return false;
    return true;
  }, [enabled, name, email, phone]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await publicApi.captureLead(packId, {
        name: name.trim(),
        email: email.trim() || null,
        phone: phone.trim() || null,
        summary: summary.trim() || null,
        website: null, // honeypot
      });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6">
        <h3 className="text-lg font-semibold">Thanks — we’ll reach out soon.</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Your details have been sent successfully.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-border bg-card p-6"
    >
      <h3 className="text-lg font-semibold">{headline}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{subheadline}</p>

      <div className="mt-5 grid gap-3">
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          disabled={!enabled || submitting}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email (optional)"
            inputMode="email"
            disabled={!enabled || submitting}
          />
          <Input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Phone (optional)"
            inputMode="tel"
            disabled={!enabled || submitting}
          />
        </div>
        <Input
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="How can we help? (optional)"
          disabled={!enabled || submitting}
        />

        {error && <p className="text-sm text-red-400">{error}</p>}
        {!enabled && (
          <p className="text-xs text-muted-foreground">
            Lead capture is disabled in preview.
          </p>
        )}

        <Button type="submit" disabled={!canSubmit || submitting}>
          {submitting ? "Submitting..." : "Submit"}
        </Button>
      </div>
    </form>
  );
}

