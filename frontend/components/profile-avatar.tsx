"use client";

import { useMemo } from "react";
import { auth } from "@/lib/api";
import { cn } from "@/lib/utils";

const DICEBEAR_BASE = "https://api.dicebear.com/9.x/shapes/svg";

/** Simple hash to derive a stable string from the token when business name is not available. */
function hashToken(str: string): string {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
  }
  return "user-" + Math.abs(h).toString(36);
}

/**
 * Profile avatar using DiceBear Shapes (abstract avatar).
 * Seed is the business name when provided, otherwise a unique value per user (from token).
 */
export function ProfileAvatar({
  className,
  businessName,
}: {
  className?: string;
  /** Business name of the current user – used as the DiceBear seed for a unique avatar. */
  businessName?: string | null;
}) {
  const src = useMemo(() => {
    const seed =
      businessName != null && String(businessName).trim()
        ? encodeURIComponent(String(businessName).trim())
        : (() => {
            const token = auth.getToken();
            return token ? encodeURIComponent(hashToken(token)) : "default";
          })();
    return `${DICEBEAR_BASE}?seed=${seed}`;
  }, [businessName]);

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt="Profile"
      className={cn("rounded-full flex-shrink-0 object-cover", className)}
    />
  );
}
