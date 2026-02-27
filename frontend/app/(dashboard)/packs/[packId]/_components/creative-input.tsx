"use client";

import { FormEvent, forwardRef } from "react";
import { Image, Mic, Send } from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import { SearchInput } from "@/components/ui/search-input";

export type CreativeInputProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  /** Called when user submits (Enter or Send click) */
  onSubmit?: (value: string) => void;
  /** Custom left adornment. Defaults to Image button. */
  leftAdornment?: React.ReactNode;
  /** Custom right adornment. Defaults to Send button (with optional Mic). */
  rightAdornment?: React.ReactNode;
  /** Show microphone button before Send. Only used when rightAdornment is not provided. */
  showMic?: boolean;
};

export const CreativeInput = forwardRef<HTMLInputElement, CreativeInputProps>(
  (
    {
      value,
      onChange,
      placeholder = "Type to Generate",
      disabled = false,
      onSubmit,
      leftAdornment,
      rightAdornment,
      showMic = false,
    },
    ref,
  ) => {
    const handleSubmit = (e: FormEvent) => {
      e.preventDefault();
      const trimmed = value.trim();
      if (!trimmed || disabled) return;
      onSubmit?.(trimmed);
    };

    const defaultLeft = (
      <IconButton
        type="button"
        variant="ghost"
        size="md"
        aria-label="Image options"
        disabled={disabled}
      >
        <Image className="h-4 w-4" />
      </IconButton>
    );

    const defaultRight = (
      <>
        {showMic && (
          <IconButton
            type="button"
            variant="ghost"
            size="md"
            aria-label="Microphone"
            disabled={disabled}
          >
            <Mic className="h-4 w-4" />
          </IconButton>
        )}
        <IconButton
          type="submit"
          variant="solid"
          size="md"
          aria-label="Send"
          disabled={!value.trim() || disabled}
        >
          <Send className="h-4 w-4" />
        </IconButton>
      </>
    );

    return (
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-0 min-w-0 w-full"
      >
        <SearchInput
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          leftAdornment={leftAdornment ?? defaultLeft}
          rightAdornment={rightAdornment ?? defaultRight}
        />
      </form>
    );
  },
);
CreativeInput.displayName = "CreativeInput";
