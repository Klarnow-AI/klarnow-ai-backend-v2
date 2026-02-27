"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { auth } from "@/api_requests/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/page-loader";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await auth.requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-[380px] space-y-6"
      >
        {/* <Link
          href="/"
          className="inline-block text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to Klarnow AI
        </Link> */}
        <h1 className="text-2xl  font-[600] text-center">Forgot password?</h1>
        {sent ? (
          <p className="text-muted-foreground text-sm">
            If an account exists for this email, you&apos;ll receive a link to
            reset your password.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <p className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
                {error}
              </p>
            )}
            <div className="space-y-2">
              <label htmlFor="forgot-email" className="sr-only">
                Email address
              </label>
              <Input
                id="forgot-email"
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="rounded-full"
              />
            </div>
            <Button
              type="submit"
              className="w-full rounded-full bg-foreground text-background hover:bg-foreground/90"
              disabled={loading}
            >
              {loading ? <Spinner className="h-5 w-5" /> : "Send reset link"}
            </Button>
          </form>
        )}
        <p className="text-center text-sm text-muted-foreground">
          <Link
            href="/"
            className="font-medium text-foreground underline-offset-2 hover:underline"
          >
            Back to log in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
