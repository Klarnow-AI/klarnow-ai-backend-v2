"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronDown } from "@/components/icons";

const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => {
  return (
    <div className="relative">
      <select
        className={cn(
          "flex h-[50px] w-full appearance-none rounded-xl border border-border bg-card px-4 py-2 pr-10 text-base sm:text-sm text-foreground transition-all",
          "focus:outline-none focus:scale-[1.02] focus:border-foreground/30",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        ref={ref}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
    </div>
  );
});
Select.displayName = "Select";

const SelectTrigger = Select;
const SelectValue: React.FC<{ placeholder?: string }> = () => null;
const SelectContent: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => <>{children}</>;
type SelectItemProps = React.OptionHTMLAttributes<HTMLOptionElement> & {
  value: string;
  children: React.ReactNode;
};

const SelectItem: React.FC<SelectItemProps> = ({
  value,
  children,
  ...props
}) => (
  <option value={value} {...props}>
    {children}
  </option>
);

export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem };
