import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const LOCAL_API_BASE = "http://localhost:8000";
const PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim();
const SERVER_API_BASE = process.env.BACKEND_URL?.trim() || PUBLIC_API_BASE;

/** Backend API base URL. Client must use NEXT_PUBLIC_API_URL; server routes may use BACKEND_URL. */
export const API_BASE =
  (typeof window === "undefined" ? SERVER_API_BASE : PUBLIC_API_BASE) ||
  LOCAL_API_BASE;

if (typeof window !== "undefined") {
  const hostname = window.location.hostname;
  const runningLocally = hostname === "localhost" || hostname === "127.0.0.1";
  const apiTargetsLocalhost =
    /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/i.test(API_BASE);

  if (!runningLocally && apiTargetsLocalhost) {
    console.error(
      "NEXT_PUBLIC_API_URL is not configured for this deployment. Set it to your hosted backend URL and rebuild the frontend.",
    );
  }
}
