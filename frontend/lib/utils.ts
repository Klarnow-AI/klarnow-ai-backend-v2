import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** In the browser, use same-origin proxy to avoid CORS; on the server use full backend URL. */
export const API_BASE =
  typeof window !== "undefined"
    ? "/api/proxy" // same-origin; app/api/proxy/[...path] forwards to backend (NEXT_PUBLIC_API_URL) with timeout
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
