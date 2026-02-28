"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type View = "main" | "code-email" | "code-entry" | "password";

export function AuthModal({
  open,
  onOpenChange,
  onRegisterSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called after successful register; parent should close auth and open onboarding. */
  onRegisterSuccess?: () => void;
}) {
  const [view, setView] = useState<View>("main");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [passwordMode, setPasswordMode] = useState<"login" | "register">(
    "login",
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingEmail, setCheckingEmail] = useState(false);
  const router = useRouter();
  const {
    checkEmailRegistered,
    requestLoginCode,
    verifyLoginCode,
    login,
    register,
  } = useAuth();

  useEffect(() => {
    if (open) {
      setView("main");
      setEmail("");
      setPassword("");
      setCode("");
      setPasswordMode("login");
      setError("");
    }
  }, [open]);

  async function handleRequestCode(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await requestLoginCode(email);
      setView("code-entry");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send code");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyCode(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await verifyLoginCode(email, code);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid or expired code");
    } finally {
      setLoading(false);
    }
  }

  async function handleEmailContinue(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setCheckingEmail(true);
    try {
      const { registered } = await checkEmailRegistered(email);
      setPasswordMode(registered ? "login" : "register");
      setView("password");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not check email. Try again.",
      );
    } finally {
      setCheckingEmail(false);
    }
  }

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (passwordMode === "login") {
        await login(email, password);
        onOpenChange(false);
      } else {
        await register(email, password);
        onRegisterSuccess?.();
        onOpenChange(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-black/50"
            onClick={() => onOpenChange(false)}
            aria-hidden
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.2 }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="auth-modal-title"
              className="pointer-events-auto w-full max-w-[420px] rounded-2xl border bg-card shadow-lg"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="relative p-6 sm:p-8">
                <button
                  type="button"
                  onClick={() => onOpenChange(false)}
                  className="absolute right-4 top-4 p-1.5 rounded-lg text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
                  aria-label="Close"
                >
                  <X className="h-5 w-5" />
                </button>
                <h2
                  id="auth-modal-title"
                  className="font-heading text-2xl  font-[600] text-foreground pr-10"
                >
                  Log In or Get Started
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  You&apos;ll get smarter responses and can upload files,
                  images, and more.
                </p>
                <AnimatePresence mode="wait">
                  {view === "main" ? (
                    <motion.div
                      key="main"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="mt-6 space-y-4"
                    >
                      {/* Button: Continue with email sign-in code */}
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full justify-center gap-3 rounded-full border-0 bg-border/40 text-foreground"
                        onClick={() => setView("code-email")}
                      >
                        Continue with email Log In code
                      </Button>

                      {/* OR */}
                      <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                          <div className="w-full h-px bg-border/40" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase tracking-wider">
                          <span className="bg-card px-3 text-muted-foreground">
                            or
                          </span>
                        </div>
                      </div>

                      {/* Email only first – Continue goes to password step */}
                      <form
                        onSubmit={handleEmailContinue}
                        className="space-y-3"
                      >
                        {error && (
                          <p className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
                            {error}
                          </p>
                        )}
                        <div className="space-y-2 mb-2">
                          <label htmlFor="auth-email" className="sr-only">
                            Email address
                          </label>
                          <Input
                            id="auth-email"
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
                          disabled={checkingEmail}
                        >
                          {checkingEmail ? (
                            <Spinner className="h-5 w-5" />
                          ) : (
                            "Continue"
                          )}
                        </Button>
                      </form>
                    </motion.div>
                  ) : view === "password" ? (
                    <motion.form
                      key="password"
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 8 }}
                      transition={{ duration: 0.2 }}
                      onSubmit={handlePasswordSubmit}
                      className="mt-6 space-y-4"
                    >
                      {error && (
                        <p className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
                          {error}
                        </p>
                      )}
                      <p className="text-sm text-muted-foreground">
                        {passwordMode === "login"
                          ? "Signing in as "
                          : "Create account for "}
                        <span className="font-medium text-foreground">
                          {email}
                        </span>
                      </p>
                      <div className="space-y-2">
                        <label htmlFor="auth-password" className="sr-only">
                          Password
                        </label>
                        <Input
                          id="auth-password"
                          type="password"
                          placeholder="Password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          required
                          autoComplete={
                            passwordMode === "login"
                              ? "current-password"
                              : "new-password"
                          }
                          className="rounded-full"
                        />
                        {passwordMode === "login" && (
                          <p className="text-right">
                            <button
                              type="button"
                              onClick={() => {
                                onOpenChange(false);
                                router.push("/forgot-password");
                              }}
                              className="text-sm font-medium text-foreground underline-offset-2 hover:no-underline"
                            >
                              Forgot password?
                            </button>
                          </p>
                        )}
                      </div>
                      <Button
                        type="submit"
                        className="w-full rounded-full bg-foreground text-background hover:bg-foreground/90"
                        disabled={loading}
                      >
                        {loading ? (
                          <Spinner className="h-5 w-5" />
                        ) : passwordMode === "login" ? (
                          "Log In"
                        ) : (
                          "Get Started"
                        )}
                      </Button>
                      <p className="text-center text-sm text-muted-foreground">
                        {passwordMode === "login" ? (
                          <>
                            Don&apos;t have an account?{" "}
                            <button
                              type="button"
                              onClick={() => setPasswordMode("register")}
                              className="font-medium text-foreground underline-offset-2 hover:no-underline hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black rounded px-1 -mx-1 transition-colors"
                            >
                              Get Started
                            </button>
                          </>
                        ) : (
                          <>
                            Already have an account?{" "}
                            <button
                              type="button"
                              onClick={() => setPasswordMode("login")}
                              className="font-medium text-foreground underline-offset-2 hover:no-underline hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black rounded px-1 -mx-1 transition-colors"
                            >
                              Log In
                            </button>
                          </>
                        )}
                      </p>
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full justify-center rounded-full border-0 bg-border/40 text-foreground"
                        onClick={() => {
                          setView("main");
                          setError("");
                        }}
                      >
                        Use a different email address
                      </Button>
                    </motion.form>
                  ) : view === "code-email" ? (
                    <motion.form
                      key="code-email"
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 8 }}
                      transition={{ duration: 0.2 }}
                      onSubmit={handleRequestCode}
                      className="mt-6 space-y-4"
                    >
                      {error && (
                        <p className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
                          {error}
                        </p>
                      )}
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full justify-center rounded-full border-0 bg-border/40 text-foreground"
                        onClick={() => {
                          setView("main");
                          setError("");
                        }}
                      >
                        Log In with email and password
                      </Button>
                      <div className="space-y-2">
                        <label htmlFor="auth-code-email" className="sr-only">
                          Email address
                        </label>
                        <Input
                          id="auth-code-email"
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
                        className="w-full rounded-full bg-foreground text-background hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
                        disabled={loading}
                      >
                        {loading ? <Spinner className="h-5 w-5" /> : "Continue"}
                      </Button>
                    </motion.form>
                  ) : (
                    <motion.form
                      key="code-entry"
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 8 }}
                      transition={{ duration: 0.2 }}
                      onSubmit={handleVerifyCode}
                      className="mt-6 space-y-4"
                    >
                      {error && (
                        <p className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
                          {error}
                        </p>
                      )}
                      <p className="text-sm text-muted-foreground">
                        We sent a 6-digit code to{" "}
                        <span className="font-medium text-foreground">
                          {email}
                        </span>
                      </p>
                      <div className="space-y-2">
                        <label htmlFor="auth-code" className="sr-only">
                          Sign-in code
                        </label>
                        <Input
                          id="auth-code"
                          type="text"
                          inputMode="numeric"
                          autoComplete="one-time-code"
                          placeholder="000000"
                          value={code}
                          onChange={(e) =>
                            setCode(
                              e.target.value.replace(/\D/g, "").slice(0, 6),
                            )
                          }
                          maxLength={6}
                          className="rounded-full text-center text-lg tracking-[0.4em] font-mono"
                        />
                      </div>
                      <Button
                        type="submit"
                        className="w-full rounded-full bg-foreground text-background hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
                        disabled={loading || code.length !== 6}
                      >
                        {loading ? <Spinner className="h-5 w-5" /> : "Continue"}
                      </Button>
                      <button
                        type="button"
                        onClick={() => {
                          setView("code-email");
                          setCode("");
                          setError("");
                        }}
                        className="w-full text-sm text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors rounded-lg py-2"
                      >
                        Use a different email address
                      </button>
                    </motion.form>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
