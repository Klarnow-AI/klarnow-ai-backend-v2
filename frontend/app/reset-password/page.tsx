"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { auth } from "@/api_requests/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/page-loader";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!token) setError("Invalid or expired link");
  }, [token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (!token) return;
    setLoading(true);
    try {
      await auth.resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Invalid or expired reset link",
      );
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
          Invalid or expired link. Request a new one below.
        </p>
        <Link
          href="/forgot-password"
          className="inline-block text-sm font-medium text-foreground underline-offset-2 hover:underline"
        >
          Request new reset link
        </Link>
        <p className="text-sm text-muted-foreground">
          <Link href="/">Back to home</Link>
        </p>
      </div>
    );
  }

  if (success) {
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground text-sm">
          Your password has been reset. You can now log in with your new
          password.
        </p>
        <Link href="/">
          <Button className="w-full rounded-full bg-foreground text-background hover:bg-foreground/90">
            Log in
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <p className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
          {error}
        </p>
      )}
      <div className="space-y-2">
        <label htmlFor="reset-password" className="sr-only">
          New password
        </label>
        <Input
          id="reset-password"
          type="password"
          placeholder="New password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="new-password"
          className="rounded-full"
        />
      </div>
      <div className="space-y-2">
        <label htmlFor="reset-confirm" className="sr-only">
          Confirm password
        </label>
        <Input
          id="reset-confirm"
          type="password"
          placeholder="Confirm password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
          autoComplete="new-password"
          className="rounded-full"
        />
      </div>
      <Button
        type="submit"
        className="w-full rounded-full bg-foreground text-background hover:bg-foreground/90"
        disabled={loading}
      >
        {loading ? <Spinner className="h-5 w-5" /> : "Reset password"}
      </Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-[380px] space-y-6"
      >
        <Link
          href="/"
          className="inline-block text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to Klarnow AI
        </Link>
        <h1 className="text-2xl  font-[600]">Reset password</h1>
        <Suspense fallback={<Spinner className="h-6 w-6" />}>
          <ResetPasswordForm />
        </Suspense>
      </motion.div>
    </div>
  );
}
