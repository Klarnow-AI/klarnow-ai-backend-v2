"use client";

import { Sun, Moon, Monitor } from "@/components/icons";
import { useTheme, type Theme } from "@/contexts/theme-context";
import { DynamicPopover } from "@/components/ui/dynamic-popover";
import { cn } from "@/lib/utils";

type ThemeOption = { value: Theme; icon: typeof Sun; label: string };

const options: ThemeOption[] = [
  { value: "light", icon: Sun, label: "Light" },
  { value: "dark", icon: Moon, label: "Dark" },
  { value: "system", icon: Monitor, label: "System" },
];

export function ThemeSettingsPopover({
  trigger,
  open,
  onOpenChange,
}: {
  trigger: React.ReactNode;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { theme, setTheme } = useTheme();

  return (
    <DynamicPopover
      open={open}
      onOpenChange={onOpenChange}
      trigger={trigger}
      placement="bottom-end"
      contentClassName="w-56 p-3"
    >
      {/* Theme row */}
      <div className="flex items-center gap-1.5 mb-3">
        {options.map((opt) => {
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
      {/* Language */}
      <div className="pt-2 border-t border-border">
        <p className="text-sm font-medium text-foreground">Language</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          Display language (coming soon)
        </p>
      </div>
    </DynamicPopover>
  );
}
