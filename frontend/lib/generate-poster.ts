import type { BrandContext } from "@/types/generation";
import {
  type PosterGenerationMode,
  extractCompletedPosterFiles,
  parsePosterFileTags,
  parsePosterResponseEnvelope,
  validatePosterTsxFile,
  validatePosterTsxFiles,
} from "@/lib/poster-output";
import {
  fetchApiResponse,
  getApiErrorFromResponse,
  getToken,
} from "@/lib/http";

export type PosterReferenceImage = {
  name: string;
  mimeType: string;
  dataUrl: string;
};

export function parseFileTags(text: string): Record<string, string> {
  return parsePosterFileTags(text);
}

type PosterGenerationRequest = {
  apiRoute: string;
  messages: { role: string; content: string }[];
  brandContext?: BrandContext | null;
  referenceImages?: PosterReferenceImage[];
  packId: string;
  generationMode?: PosterGenerationMode;
  authToken?: string | null;
};

export type PosterGenerationResult = {
  summary: string;
  assistantText: string;
  files: Record<string, string>;
};

export async function streamPosterGeneration(
  request: PosterGenerationRequest,
  options?: {
    onFile?: (name: string, code: string) => void | Promise<void>;
  },
): Promise<PosterGenerationResult> {
  const {
    apiRoute,
    messages,
    brandContext,
    referenceImages,
    packId,
    generationMode,
    authToken,
  } = request;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = authToken ?? getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (!packId) {
    throw new Error("Missing pack ID for poster generation.");
  }

  let res: Response;
  res = await fetchApiResponse(apiRoute, {
    method: "POST",
    authToken: token,
    headers,
    body: JSON.stringify({
      messages,
      brandContext: brandContext ?? undefined,
      packId: packId ?? undefined,
      generationMode: generationMode ?? "manual",
      referenceImages:
        referenceImages && referenceImages.length > 0
          ? referenceImages
          : undefined,
    }),
  });

  if (!res.ok) {
    throw await getApiErrorFromResponse(res, "Poster generation failed");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let accumulated = "";
  const seenFileNames = new Set<string>();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    accumulated += decoder.decode(value, { stream: true });

    const completedFiles = extractCompletedPosterFiles(accumulated, seenFileNames);
    for (const [name, code] of Object.entries(completedFiles)) {
      const validation = validatePosterTsxFile(name, code);
      if (!validation.ok || !validation.file) {
        throw new Error(validation.errors.join(" "));
      }
      seenFileNames.add(validation.fileName);
      await options?.onFile?.(validation.fileName, validation.file);
    }
  }
  accumulated += decoder.decode();

  const parsed = parsePosterResponseEnvelope(accumulated);
  if (Object.keys(parsed.files).length === 0) {
    return parsed;
  }

  const validation = validatePosterTsxFiles(parsed.files, {
    mode: generationMode ?? "manual",
  });
  if (!validation.ok) {
    throw new Error(validation.errors.join(" "));
  }

  return {
    ...parsed,
    files: validation.files,
  };
}

export async function generatePosters(
  apiRoute: string,
  userContent: string,
  brandContext?: BrandContext | null,
  referenceImages?: PosterReferenceImage[],
  packId?: string,
  authToken?: string | null,
): Promise<Record<string, string>> {
  if (!packId) {
    throw new Error("Missing pack ID for poster generation.");
  }

  const parsed = await streamPosterGeneration({
    apiRoute,
    messages: [{ role: "user", content: userContent }],
    brandContext,
    referenceImages,
    packId,
    generationMode: "manual",
    authToken,
  });

  if (Object.keys(parsed.files).length === 0) {
    throw new Error(parsed.assistantText || parsed.summary || "No poster files were generated.");
  }

  return parsed.files;
}
