import type { BrandContext } from "@/app/api/generate/route";

export type PosterReferenceImage = {
  name: string;
  mimeType: string;
  dataUrl: string;
};

export function parseFileTags(text: string): Record<string, string> {
  const files: Record<string, string> = {};
  const regex = /<file name="([^"]+)">([\s\S]*?)<\/file>/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const name = match[1].startsWith("/") ? match[1] : `/${match[1]}`;
    files[name] = match[2].trim();
  }
  return files;
}

export async function generatePosters(
  apiRoute: string,
  userContent: string,
  brandContext?: BrandContext | null,
  referenceImages?: PosterReferenceImage[],
  packId?: string,
  authToken?: string | null,
): Promise<Record<string, string>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const res = await fetch(apiRoute, {
    method: "POST",
    headers,
    body: JSON.stringify({
      messages: [{ role: "user", content: userContent }],
      brandContext: brandContext ?? undefined,
      packId: packId ?? undefined,
      referenceImages:
        referenceImages && referenceImages.length > 0
          ? referenceImages
          : undefined,
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    let message: string;
    try {
      const parsed = JSON.parse(errText) as { error?: string };
      message = parsed.error ?? errText;
    } catch {
      message = errText;
    }
    throw new Error(message);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let accumulated = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    accumulated += decoder.decode(value, { stream: true });
  }

  return parseFileTags(accumulated);
}
