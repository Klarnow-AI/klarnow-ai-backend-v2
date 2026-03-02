"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface CheckboxProps extends Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "type" | "checked"
> {
  checked?: boolean | "indeterminate";
  onCheckedChange?: (checked: boolean) => void;
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, checked, onCheckedChange, onChange, ...props }, ref) => {
    const internalRef = React.useRef<HTMLInputElement | null>(null);
    const setRefs = React.useCallback(
      (el: HTMLInputElement | null) => {
        internalRef.current = el;
        if (typeof ref === "function") ref(el);
        else if (ref) ref.current = el;
      },
      [ref],
    );

    React.useEffect(() => {
      const el = internalRef.current;
      if (!el) return;
      if (checked === "indeterminate") {
        el.indeterminate = true;
        el.checked = false;
      } else {
        el.indeterminate = false;
        el.checked = !!checked;
      }
    }, [checked]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange?.(e);
      onCheckedChange?.(e.target.checked);
    };

    const isChecked = checked === "indeterminate" ? false : !!checked;

    return (
      <input
        type="checkbox"
        ref={setRefs}
        checked={isChecked}
        onChange={handleChange}
        className={cn(
          "h-4 w-4 shrink-0 rounded border border-border bg-card shadow-sm transition-transform",
          "focus-visible:outline-none focus-visible:scale-110",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "accent-primary",
          className,
        )}
        {...props}
      />
    );
  },
);
Checkbox.displayName = "Checkbox";

export { Checkbox };
