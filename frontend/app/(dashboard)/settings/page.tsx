"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Settings as SettingsIcon,
  Wallet,
  Loader2,
  Sun,
  Moon,
  Monitor,
  User as UserIcon,
  LogOut,
  AlertCircle,
  Lock,
  Receipt,
  Bell,
} from "@/components/icons";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogBody,
  DialogClose,
} from "@/components/ui/dialog";
import { useTheme, type Theme } from "@/contexts/theme-context";
import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";
import { revenue } from "@/api_requests/revenue";
import { auth } from "@/api_requests/auth";
import { me } from "@/api_requests/me";
import {
  subscriptionApi,
  type SubscriptionRead,
} from "@/api_requests/subscription";
import { ProfileAvatar } from "@/components/profile-avatar";

const themeOptions: { value: Theme; icon: typeof Sun; label: string }[] = [
  { value: "light", icon: Sun, label: "Light" },
  { value: "dark", icon: Moon, label: "Dark" },
  { value: "system", icon: Monitor, label: "System" },
];

export default function SettingsPage() {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const { logout } = useAuth();

  const [connectStatus, setConnectStatus] = useState<{
    connected: boolean;
    onboarding_complete: boolean;
  } | null>(null);
  const [connectLoading, setConnectLoading] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const [profile, setProfile] = useState<{
    email: string;
    created_at: string;
    last_activity_at: string | null;
  } | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);

  const [subscription, setSubscription] = useState<SubscriptionRead | null>(
    null,
  );
  const [subscriptionLoading, setSubscriptionLoading] = useState(true);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changePasswordLoading, setChangePasswordLoading] = useState(false);
  const [changePasswordError, setChangePasswordError] = useState<string | null>(
    null,
  );
  const [changePasswordSuccess, setChangePasswordSuccess] = useState(false);

  useEffect(() => {
    revenue
      .getConnectStatus()
      .then((r) => setConnectStatus(r))
      .catch(() =>
        setConnectStatus({ connected: false, onboarding_complete: false }),
      );
  }, []);

  useEffect(() => {
    me.getProfile()
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => setProfileLoading(false));
  }, []);

  useEffect(() => {
    subscriptionApi
      .get()
      .then(setSubscription)
      .catch(() => setSubscription(null))
      .finally(() => setSubscriptionLoading(false));
  }, []);

  const handleConnectStripe = async () => {
    setConnectLoading(true);
    setConnectError(null);
    try {
      const { url } = await revenue.createConnectOnboardingLink();
      if (url) window.location.href = url;
      else setConnectError("No redirect URL returned");
    } catch (e) {
      setConnectError(
        e instanceof Error ? e.message : "Failed to start Stripe Connect",
      );
    } finally {
      setConnectLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== "delete") return;
    setDeleteLoading(true);
    setDeleteError(null);
    try {
      await auth.deleteAccount();
      router.replace("/");
      window.location.reload();
    } catch (e) {
      setDeleteError(
        e instanceof Error ? e.message : "Failed to delete account",
      );
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setChangePasswordError("Passwords do not match");
      return;
    }
    if (newPassword.length < 8) {
      setChangePasswordError("Password must be at least 8 characters");
      return;
    }
    setChangePasswordLoading(true);
    setChangePasswordError(null);
    setChangePasswordSuccess(false);
    try {
      await auth.changePassword(currentPassword, newPassword);
      setChangePasswordSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (e) {
      setChangePasswordError(
        e instanceof Error ? e.message : "Failed to change password",
      );
    } finally {
      setChangePasswordLoading(false);
    }
  };

  const formatDate = (iso: string) => {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    } catch {
      return iso;
    }
  };

  type Section =
    | "general"
    | "account"
    | "security"
    | "billing"
    | "notifications";
  const [section, setSection] = useState<Section>("account");

  const navItems: { id: Section; label: string; icon: typeof SettingsIcon }[] =
    [
      { id: "general", label: "General", icon: SettingsIcon },
      { id: "account", label: "Account", icon: UserIcon },
      { id: "security", label: "Security", icon: Lock },
      { id: "billing", label: "Billing", icon: Receipt },
      { id: "notifications", label: "Notifications", icon: Bell },
    ];

  return (
    <div className="flex flex-1 min-h-0">
      {/* Sidebar nav */}
      <aside className="shrink-0 w-56 p-4 pt-60 flex flex-col items-start">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 mb-4">
          Settings
        </p>
        <nav className="space-y-0.5 w-full">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = section === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSection(item.id)}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-0 hover:scale-[1.02]",
                  isActive
                    ? "font-bold text-primary scale-105"
                    : "text-muted-foreground  /50 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Scrollable content */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        <div className="max-w-2xl p-8 pb-16">
          {/* General */}
          {section === "general" && (
            <>
              <div className="mb-8">
                <h2 className="text-xl font-semibold tracking-tight">
                  General
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  App appearance and display.
                </p>
              </div>
              <div className="space-y-6">
                <div>
                  <Label className="text-sm font-medium mb-2 block">
                    Theme
                  </Label>
                  <div className="flex items-center gap-1.5">
                    {themeOptions.map((opt) => {
                      const Icon = opt.icon;
                      const isSelected = theme === opt.value;
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => setTheme(opt.value)}
                          className={cn(
                            "flex h-9 w-9 items-center justify-center rounded-lg border transition-all focus-visible:outline-none focus-visible:ring-0",
                            isSelected
                              ? "font-bold text-primary scale-105 border-transparent"
                              : "border-transparent text-muted-foreground  /50 hover:scale-105",
                          )}
                          title={opt.label}
                          aria-label={opt.label}
                        >
                          <Icon className="h-4 w-4" />
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div className="pt-4 border-t border-border">
                  <Label className="text-sm font-medium">Language</Label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Display language (coming soon)
                  </p>
                </div>
                <div className="pt-4 border-t border-border">
                  <Label className="text-sm font-medium">
                    API keys & integrations
                  </Label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Webhooks and integrations (coming soon)
                  </p>
                </div>
              </div>
            </>
          )}

          {/* Account */}
          {section === "account" && (
            <>
              <div className="mb-8">
                <h2 className="text-xl font-semibold tracking-tight">
                  Account
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Your account information.
                </p>
              </div>
              <div className="space-y-6">
                {profileLoading ? (
                  <p className="text-sm text-muted-foreground">Loading…</p>
                ) : profile ? (
                  <div className="space-y-6">
                    <div className="flex items-start gap-4">
                      <ProfileAvatar
                        className="h-16 w-16"
                        businessName={profile.email}
                      />
                      <div className="flex-1 space-y-4">
                        <div>
                          <Label className="text-muted-foreground text-xs">
                            Email
                          </Label>
                          <p className="text-sm font-medium mt-1">
                            {profile.email}
                          </p>
                        </div>
                        <div>
                          <Label className="text-muted-foreground text-xs">
                            Display name
                          </Label>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            Add a display name (coming soon)
                          </p>
                        </div>
                        <div>
                          <Label className="text-muted-foreground text-xs">
                            Change email
                          </Label>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            Update your email address (coming soon)
                          </p>
                        </div>
                        <div>
                          <Label className="text-muted-foreground text-xs">
                            Social links
                          </Label>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            Add X, LinkedIn, etc. (coming soon)
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <Label className="text-muted-foreground text-xs">
                          Member since
                        </Label>
                        <p className="text-sm mt-1">
                          {formatDate(profile.created_at)}
                        </p>
                      </div>
                      <div>
                        <Label className="text-muted-foreground text-xs">
                          Last active
                        </Label>
                        <p className="text-sm mt-1">
                          {profile.last_activity_at
                            ? formatDate(profile.last_activity_at)
                            : "—"}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Could not load profile.
                  </p>
                )}
                <div className="pt-6">
                  <Label className="text-sm font-medium text-destructive block mb-2">
                    Danger zone
                  </Label>
                  <p className="text-xs text-muted-foreground mb-3">
                    Permanently delete your account and all data. This cannot be
                    undone.
                  </p>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setDeleteDialogOpen(true)}
                  >
                    Delete account
                  </Button>
                </div>
              </div>
            </>
          )}

          {/* Security */}
          {section === "security" && (
            <>
              <div className="mb-8">
                <h2 className="text-xl font-semibold tracking-tight">
                  Security
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Password and sign out.
                </p>
              </div>
              <div className="space-y-6">
                <div>
                  <Label className="text-sm font-medium mb-2 block">
                    Change password
                  </Label>
                  <div className="space-y-3 max-w-sm">
                    <Input
                      type="password"
                      placeholder="Current password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                    />
                    <Input
                      type="password"
                      placeholder="New password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                    <Input
                      type="password"
                      placeholder="Confirm new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                    {changePasswordError && (
                      <p className="text-sm text-destructive">
                        {changePasswordError}
                      </p>
                    )}
                    {changePasswordSuccess && (
                      <p className="text-sm text-green-600 dark:text-green-400">
                        Password updated.
                      </p>
                    )}
                    <Button
                      onClick={handleChangePassword}
                      disabled={
                        changePasswordLoading ||
                        !currentPassword ||
                        !newPassword ||
                        !confirmPassword
                      }
                    >
                      {changePasswordLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Update password"
                      )}
                    </Button>
                  </div>
                </div>
                <div className="pt-6 border-t border-border">
                  <Button variant="outline" onClick={logout} className="gap-2">
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </Button>
                </div>
              </div>
            </>
          )}

          {/* Billing */}
          {section === "billing" && (
            <>
              <div className="mb-8">
                <h2 className="text-xl font-semibold tracking-tight">
                  Billing
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Your plan, credits, and payments.
                </p>
              </div>
              <div className="space-y-8">
                <div>
                  <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Subscription
                  </Label>
                  {subscriptionLoading ? (
                    <p className="text-sm text-muted-foreground mt-2">
                      Loading…
                    </p>
                  ) : subscription ? (
                    <div className="mt-2 space-y-2">
                      <div className="flex items-center gap-4">
                        <span className="text-sm font-medium capitalize">
                          {subscription.plan}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {subscription.credits_remaining} /{" "}
                          {subscription.credits_total} credits
                        </span>
                      </div>
                      {subscription.plan === "free" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            subscriptionApi
                              .upgradePlan("standard")
                              .then(() =>
                                subscriptionApi.get().then(setSubscription),
                              )
                          }
                        >
                          Upgrade plan
                        </Button>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground mt-2">
                      Could not load subscription.
                    </p>
                  )}
                </div>
                <div className="pt-6 border-t border-border">
                  <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Stripe Connect
                  </Label>
                  <p className="text-sm text-muted-foreground mt-2 mb-4">
                    Connect your Stripe account to create shareable invoice
                    payment links.
                  </p>
                  {connectError && (
                    <p className="text-sm text-destructive mb-2">
                      {connectError}
                    </p>
                  )}
                  {connectStatus?.connected &&
                  connectStatus?.onboarding_complete ? (
                    <p className="text-sm text-muted-foreground">
                      Stripe connected.{" "}
                      <Link
                        href="/invoices"
                        className="text-primary hover:underline"
                      >
                        Create payment links
                      </Link>
                    </p>
                  ) : connectStatus?.connected ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleConnectStripe}
                      disabled={connectLoading}
                    >
                      {connectLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Complete Stripe setup"
                      )}
                    </Button>
                  ) : (
                    <Button
                      onClick={handleConnectStripe}
                      disabled={connectLoading}
                    >
                      {connectLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Connect Stripe"
                      )}
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}

          {/* Notifications */}
          {section === "notifications" && (
            <>
              <div className="mb-8">
                <h2 className="text-xl font-semibold tracking-tight">
                  Notifications
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage how we notify you.
                </p>
              </div>
              <div>
                <Label className="text-sm font-medium">
                  Email notifications
                </Label>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Notify me about follow-ups, new leads (coming soon)
                </p>
              </div>
            </>
          )}
        </div>
      </main>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Delete account</DialogTitle>
            <DialogDescription>
              This will permanently delete your account and all your data
              (packs, leads, proposals, conversations, etc.). This action cannot
              be undone.
            </DialogDescription>
            <DialogClose onClose={() => setDeleteDialogOpen(false)} />
          </DialogHeader>
          <DialogBody>
            <p className="text-sm text-muted-foreground mb-4">
              Type <strong>delete</strong> to confirm:
            </p>
            <Input
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder="delete"
              className="mb-4"
            />
            {deleteError && (
              <p className="text-sm text-destructive mb-4">{deleteError}</p>
            )}
            <div className="flex gap-2">
              <Button
                variant="destructive"
                onClick={handleDeleteAccount}
                disabled={deleteConfirmText !== "delete" || deleteLoading}
              >
                {deleteLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Delete account"
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
              >
                Cancel
              </Button>
            </div>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </div>
  );
}
