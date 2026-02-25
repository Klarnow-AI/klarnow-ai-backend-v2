"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Sun } from "@/components/icons";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/contexts/theme-context";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { ThemeSettingsPopover } from "@/components/theme-settings-popover";
import { ProfileDropdown } from "@/components/profile-dropdown";
import { ProfileAvatar } from "@/components/profile-avatar";

type PublicHeaderProps = {
  /** When authenticated, called when user clicks Dashboard. If not provided, navigates to /packs */
  onDashboardClick?: (e: React.MouseEvent) => void;
  /** When not authenticated, called when user clicks Sign in or Sign up */
  onAuthClick?: () => void;
  /** Whether to show Install and About links in the center. Default true */
  showInstallAbout?: boolean;
};

export function PublicHeader({
  onDashboardClick,
  onAuthClick,
  showInstallAbout = true,
}: PublicHeaderProps) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const { resolved: themeResolved } = useTheme();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const logoSrc =
    themeResolved === "dark"
      ? "/logos/logo_white.svg"
      : "/logos/logo_black.svg";

  function handleDashboardClick(e: React.MouseEvent) {
    e.preventDefault();
    if (onDashboardClick) {
      onDashboardClick(e);
    } else {
      router.push("/packs");
    }
  }

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="relative flex items-center justify-between px-6 py-4"
    >
      <Link href="/" className="flex items-center gap-2 flex-shrink-0">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-full overflow-hidden">
          <Image
            src={logoSrc}
            alt="Klarnow AI"
            width={36}
            height={36}
            className="object-contain"
          />
        </div>
      </Link>
      {showInstallAbout && !isLoading && (
        <nav
          className="absolute left-1/2 -translate-x-1/2 flex items-center gap-6"
          aria-label="Main"
        >
          <Link
            href="/install"
            className="text-sm text-foreground/70 no-underline hover:text-foreground transition-colors"
          >
            Install
          </Link>
          <Link
            href="/about"
            className="text-sm text-foreground/70 no-underline hover:text-foreground transition-colors"
          >
            About
          </Link>
        </nav>
      )}
      <nav className="flex items-center gap-2 flex-shrink-0">
        {!isLoading && (
          <>
            {isAuthenticated ? (
              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={handleDashboardClick}
                  className="text-sm text-foreground/50 no-underline hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors rounded-lg px-2 py-1 -mx-2 -my-1"
                >
                  Dashboard
                </button>
                <ProfileDropdown
                  open={profileOpen}
                  onOpenChange={setProfileOpen}
                  className="flex h-11 w-11 items-center justify-center rounded-full border-[0.2px] border-border bg-card overflow-hidden"
                >
                  <ProfileAvatar className="h-full w-full" />
                </ProfileDropdown>
              </div>
            ) : (
              <>
                <ThemeSettingsPopover
                  open={settingsOpen}
                  onOpenChange={setSettingsOpen}
                  trigger={
                    <IconButton
                      variant="ghost"
                      size="md"
                      className="rounded-lg"
                      aria-label="Theme"
                    >
                      <Sun className="h-5 w-5" />
                    </IconButton>
                  }
                />
                <Button
                  variant="outline"
                  size="sm"
                  className="border-border bg-card"
                  onClick={onAuthClick}
                >
                  Sign in
                </Button>
                <Button
                  size="sm"
                  className="bg-foreground text-background hover:bg-foreground/90"
                  onClick={onAuthClick}
                >
                  Sign up
                </Button>
              </>
            )}
          </>
        )}
      </nav>
    </motion.header>
  );
}
