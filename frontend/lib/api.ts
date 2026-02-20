/**
 * Re-exports API clients and types for backward compatibility.
 * Prefer importing from @/api_requests/* and @/types/api-types for new code.
 */

export { api } from "./http";
export { API_BASE } from "./utils";
export { auth } from "@/api_requests/auth";
export { me } from "@/api_requests/me";
export { packs } from "@/api_requests/packs";
export { chat } from "@/api_requests/chat";
export { creative } from "@/api_requests/creative";

export type {
  AuthAccessToken,
  AuthCheckEmail,
  LandingPack,
  LandingContext,
  Pack,
  PackListResponse,
  Conversation,
  Message,
  ConversationListResponse,
  MessageListResponse,
} from "@/types/api-types";
