"use client";

import Link from "next/link";
import {
  User,
  LogOut,
  Sun,
  Moon,
  Monitor,
} from "@/components/icons";
import { useAuth } from "@/contexts/auth-context";
import { useTheme, type Theme } from "@/contexts/theme-context";
import { DynamicPopover } from "@/components/ui/dynamic-popover";
import { cn } from "@/lib/utils";

export function ProfileDropdown({
  open,
  onOpenChange,
  children,
  className,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children?: React.ReactNode;
  className?: string;
}) {
  const { logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const themeOptions: { value: Theme; icon: typeof Sun; label: string }[] = [
    { value: "light", icon: Sun, label: "Light" },
    { value: "dark", icon: Moon, label: "Dark" },
    { value: "system", icon: Monitor, label: "System" },
  ];

  return (
    <DynamicPopover
      open={open}
      onOpenChange={onOpenChange}
      trigger={
        <button
          type="button"
          className={cn(
            className,
            "transition-all hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black focus-visible:outline-none focus-visible:ring-0 hover:scale-105",
          )}
          aria-label="Profile menu"
          aria-expanded={open}
        >
          {children}
        </button>
      }
      placement="bottom-end"
      contentClassName="w-52 py-1"
    >
      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-border">
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
                  ? " font-[600] text-primary scale-105 border-transparent"
                  : "border-transparent text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black hover:scale-105",
              )}
              title={opt.label}
              aria-label={opt.label}
            >
              <Icon className="h-4 w-4" />
            </button>
          );
        })}
      </div>
      <Link
        href="/settings"
        className="flex items-center gap-3 px-3 py-2.5 text-sm text-foreground hover:bg-white/5 hover:scale-[1.02] transition-all focus-visible:outline-none focus-visible:ring-0"
        onClick={() => onOpenChange(false)}
      >
        <User className="h-4 w-4 shrink-0 text-muted-foreground" />
        View account
      </Link>
      <button
        type="button"
        onClick={() => {
          void logout();
          onOpenChange(false);
        }}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-sm text-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-all text-left focus-visible:outline-none focus-visible:ring-0 hover:scale-[1.02]"
      >
        <LogOut className="h-4 w-4 shrink-0 text-muted-foreground" />
        Sign out
      </button>
    </DynamicPopover>
  );
}
