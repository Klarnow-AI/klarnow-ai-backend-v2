import { create } from "zustand";
import {
  type ConnectivityIssueKind,
  getFriendlyErrorMessage,
} from "@/lib/request-errors";

type ConnectivityIssue = {
  kind: ConnectivityIssueKind;
  message: string;
};

type ConnectivityStore = {
  issue: ConnectivityIssue | null;
  setIssue: (issue: ConnectivityIssue) => void;
  clearIssue: () => void;
};

export const useConnectivityStore = create<ConnectivityStore>((set) => ({
  issue: null,
  setIssue: (issue) => set({ issue }),
  clearIssue: () => set({ issue: null }),
}));

export function reportConnectivityIssue(
  kind: ConnectivityIssueKind,
  message = getFriendlyErrorMessage(kind),
): void {
  const current = useConnectivityStore.getState().issue;
  if (current?.kind === kind && current.message === message) return;
  useConnectivityStore.getState().setIssue({ kind, message });
}

export function clearConnectivityIssue(): void {
  if (!useConnectivityStore.getState().issue) return;
  useConnectivityStore.getState().clearIssue();
}
