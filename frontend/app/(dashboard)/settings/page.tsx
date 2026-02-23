"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Settings as SettingsIcon, Wallet, Loader2 } from "@/components/icons";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { revenue } from "@/api_requests/revenue";

export default function SettingsPage() {
  const [connectStatus, setConnectStatus] = useState<{
    connected: boolean;
    onboarding_complete: boolean;
  } | null>(null);
  const [connectLoading, setConnectLoading] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  useEffect(() => {
    revenue
      .getConnectStatus()
      .then((r) => setConnectStatus(r))
      .catch(() => setConnectStatus({ connected: false, onboarding_complete: false }));
  }, []);

  const handleConnectStripe = async () => {
    setConnectLoading(true);
    setConnectError(null);
    try {
      const { url } = await revenue.createConnectOnboardingLink();
      if (url) window.location.href = url;
      else setConnectError("No redirect URL returned");
    } catch (e) {
      setConnectError(e instanceof Error ? e.message : "Failed to start Stripe Connect");
    } finally {
      setConnectLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Preferences and account.
        </p>
      </motion.div>

      <Card asMotion delay={0.1} className="mb-6">
        <CardHeader className="flex flex-row items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-foreground">
            <SettingsIcon className="h-6 w-6" />
          </div>
          <div>
            <CardTitle>Settings</CardTitle>
            <CardDescription>App and account settings.</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Theme, notifications, API keys (if any).
          </p>
        </CardContent>
      </Card>

      <Card asMotion delay={0.15}>
        <CardHeader className="flex flex-row items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-foreground">
            <Wallet className="h-6 w-6" />
          </div>
          <div>
            <CardTitle>Stripe Connect</CardTitle>
            <CardDescription>
              Connect your Stripe account to create shareable invoice payment links. Payments go to your Stripe account.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {connectError && (
            <p className="text-sm text-destructive">{connectError}</p>
          )}
          {connectStatus?.connected && connectStatus?.onboarding_complete ? (
            <p className="text-sm text-muted-foreground">
              Stripe connected. You can create payment links from the{" "}
              <Link href="/invoices" className="text-primary hover:underline">Invoices</Link> page.
            </p>
          ) : connectStatus?.connected ? (
            <p className="text-sm text-muted-foreground">
              Onboarding in progress. Complete the steps in Stripe, or{" "}
              <Button variant="link" className="p-0 h-auto text-primary" onClick={handleConnectStripe} disabled={connectLoading}>
                {connectLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "try again"}.
              </Button>
            </p>
          ) : (
            <Button onClick={handleConnectStripe} disabled={connectLoading}>
              {connectLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Connect Stripe"}
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
