import { api } from "@/lib/http";

export type BugReportBody = {
  message: string;
  path?: string | null;
};

type BugReportResponse = {
  status: "sent";
};

export const feedbackApi = {
  sendBugReport: (body: BugReportBody) =>
    api<BugReportResponse>("/api/v1/feedback/bug-report", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
