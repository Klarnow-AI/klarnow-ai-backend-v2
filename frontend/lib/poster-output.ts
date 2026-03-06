export type PosterSizeId = "4x5" | "9x16" | "16x9" | "1x1";
export type PosterVariantId = "v1" | "v2" | "v3" | "v4";
export type PosterGenerationMode = "auto" | "manual";

export type PosterConversationMessage = {
  role: "user" | "assistant";
  content: string;
  meta?: {
    kind?: "background_generation";
    label?: string;
    taskLabel?: string;
    mode?: string;
    modeLabel?: string;
  };
};

export type PosterSizeSpec = {
  id: PosterSizeId;
  label: string;
  width: number;
  height: number;
};

export const POSTER_SIZE_SPECS: Record<PosterSizeId, PosterSizeSpec> = {
  "4x5": { id: "4x5", label: "4x5 Feed", width: 1080, height: 1350 },
  "9x16": { id: "9x16", label: "9x16 Story", width: 1080, height: 1920 },
  "16x9": {
    id: "16x9",
    label: "16x9 Landscape",
    width: 1920,
    height: 1080,
  },
  "1x1": { id: "1x1", label: "1x1 Square", width: 1080, height: 1080 },
};

const POSTER_VARIANTS: PosterVariantId[] = ["v1", "v2", "v3", "v4"];
const MANUAL_POSTER_VARIANTS: PosterVariantId[] = ["v1"];
const POSTER_SIZES: PosterSizeId[] = ["4x5", "9x16", "16x9", "1x1"];

const FILE_TAG_REGEX = /<file name="([^"]+)">([\s\S]*?)<\/file>/g;
const FENCED_CODE_BLOCK_REGEX = /```(?:[a-zA-Z0-9_-]+)?\s*\n([\s\S]*?)```/g;
const SUMMARY_TAG_REGEX = /<summary>([\s\S]*?)<\/summary>/i;
const FENCED_FILE_NAME_COMMENT_REGEX =
  /^\/\/\s*(?:file\s*:\s*)?(\/?poster-(?:v[1-4])-(?:4x5|9x16|16x9|1x1)\.tsx)\s*$/i;

export type PosterFileMeta = {
  variant: PosterVariantId;
  size: PosterSizeId;
  width: number;
  height: number;
};

export type PosterValidationResult = {
  ok: boolean;
  errors: string[];
  missingFiles: string[];
  extraFiles: string[];
  files: Record<string, string>;
  metadata: Record<string, PosterFileMeta>;
};

export type ParsedPosterResponse = {
  summary: string;
  assistantText: string;
  files: Record<string, string>;
};

type ParsedPosterFileBlock = {
  name: string;
  code: string;
  start: number;
  end: number;
};

export type PosterSingleFileValidationResult = {
  ok: boolean;
  errors: string[];
  fileName: string;
  file: string | null;
  meta: PosterFileMeta | null;
};

export function buildPosterFileName(
  variant: PosterVariantId,
  size: PosterSizeId,
): string {
  return `/poster-${variant}-${size}.tsx`;
}

export const EXPECTED_POSTER_FILENAMES = POSTER_VARIANTS.flatMap((variant) =>
  POSTER_SIZES.map((size) => buildPosterFileName(variant, size)),
);

export function getExpectedPosterFileNames(
  mode: PosterGenerationMode = "auto",
): string[] {
  const variants = mode === "manual" ? MANUAL_POSTER_VARIANTS : POSTER_VARIANTS;
  return variants.flatMap((variant) =>
    POSTER_SIZES.map((size) => buildPosterFileName(variant, size)),
  );
}

export function normalizePosterFileName(name: string): string {
  return name.startsWith("/") ? name : `/${name}`;
}

export function parsePosterSummary(text: string): string {
  const match = text.match(SUMMARY_TAG_REGEX);
  return match ? match[1].trim() : "";
}

function parseFencedPosterFileBlock(
  blockText: string,
): { name: string; code: string } | null {
  const normalized = blockText.replace(/\r\n/g, "\n").trim();
  if (!normalized) return null;

  const lines = normalized.split("\n");
  while (lines.length > 0 && lines[0].trim().length === 0) {
    lines.shift();
  }
  if (lines.length === 0) return null;

  const firstLine = lines[0].trim();
  const fileNameMatch = firstLine.match(FENCED_FILE_NAME_COMMENT_REGEX);
  if (!fileNameMatch) return null;

  const code = lines.slice(1).join("\n").trim();
  if (!code) return null;

  return {
    name: normalizePosterFileName(fileNameMatch[1]),
    code,
  };
}

function collectPosterFileBlocks(text: string): ParsedPosterFileBlock[] {
  const blocks: ParsedPosterFileBlock[] = [];
  let match: RegExpExecArray | null;

  FILE_TAG_REGEX.lastIndex = 0;
  while ((match = FILE_TAG_REGEX.exec(text)) !== null) {
    blocks.push({
      name: normalizePosterFileName(match[1].trim()),
      code: match[2].trim(),
      start: match.index,
      end: match.index + match[0].length,
    });
  }

  FENCED_CODE_BLOCK_REGEX.lastIndex = 0;
  while ((match = FENCED_CODE_BLOCK_REGEX.exec(text)) !== null) {
    const parsed = parseFencedPosterFileBlock(match[1]);
    if (!parsed) continue;
    blocks.push({
      name: parsed.name,
      code: parsed.code,
      start: match.index,
      end: match.index + match[0].length,
    });
  }

  return blocks.sort((a, b) => a.start - b.start);
}

export function parsePosterFileTags(text: string): Record<string, string> {
  const files: Record<string, string> = {};
  for (const block of collectPosterFileBlocks(text)) {
    files[block.name] = block.code;
  }

  return files;
}

export function extractCompletedPosterFiles(
  text: string,
  seenFileNames: ReadonlySet<string> = new Set(),
): Record<string, string> {
  const files: Record<string, string> = {};
  for (const block of collectPosterFileBlocks(text)) {
    if (seenFileNames.has(block.name)) continue;
    files[block.name] = block.code;
  }

  return files;
}

export function stripPosterEnvelopeTags(text: string): string {
  const summaryMatch = SUMMARY_TAG_REGEX.exec(text);
  const ranges: Array<{ start: number; end: number }> = [];

  if (summaryMatch && summaryMatch.index >= 0) {
    ranges.push({
      start: summaryMatch.index,
      end: summaryMatch.index + summaryMatch[0].length,
    });
  }

  for (const block of collectPosterFileBlocks(text)) {
    ranges.push({ start: block.start, end: block.end });
  }

  if (ranges.length === 0) return text.trim();

  ranges.sort((a, b) => a.start - b.start);
  const merged: Array<{ start: number; end: number }> = [];
  for (const range of ranges) {
    const last = merged[merged.length - 1];
    if (!last || range.start > last.end) {
      merged.push({ ...range });
    } else if (range.end > last.end) {
      last.end = range.end;
    }
  }

  let cursor = 0;
  let stripped = "";
  for (const range of merged) {
    stripped += text.slice(cursor, range.start);
    cursor = range.end;
  }
  stripped += text.slice(cursor);

  return stripped.trim();
}

export function parsePosterResponseEnvelope(text: string): ParsedPosterResponse {
  return {
    summary: parsePosterSummary(text),
    files: parsePosterFileTags(text),
    assistantText: stripPosterEnvelopeTags(text),
  };
}

function parsePosterMetaFromName(name: string): PosterFileMeta | null {
  const normalized = normalizePosterFileName(name);
  const match = normalized.match(/^\/poster-(v[1-4])-(4x5|9x16|16x9|1x1)\.tsx$/i);
  if (!match) return null;

  const variant = match[1].toLowerCase() as PosterVariantId;
  const size = match[2] as PosterSizeId;
  const spec = POSTER_SIZE_SPECS[size];

  return {
    variant,
    size,
    width: spec.width,
    height: spec.height,
  };
}

function hasDimensionValue(
  code: string,
  property: "width" | "height",
  expected: number,
): boolean {
  const numberPattern = new RegExp(
    `${property}\\s*:\\s*${expected}(?:\\b|\\s*[,}])`,
    "i",
  );
  const pxStringPattern = new RegExp(
    `${property}\\s*:\\s*[\"']${expected}px[\"']`,
    "i",
  );
  return numberPattern.test(code) || pxStringPattern.test(code);
}

function validateTsxComponentShape(fileName: string, code: string): string[] {
  const errors: string[] = [];

  if (!fileName.toLowerCase().endsWith(".tsx")) {
    errors.push(`${fileName}: file extension must be .tsx.`);
  }

  if (!/export\s+default\s+/m.test(code)) {
    errors.push(`${fileName}: missing default export.`);
  }

  if (/^\s*import\s+/m.test(code)) {
    errors.push(`${fileName}: imports are not allowed. File must be self-contained.`);
  }

  if (/className\s*=/.test(code)) {
    errors.push(`${fileName}: className is not allowed. Use inline style objects only.`);
  }

  if (/<style[\s>]/i.test(code)) {
    errors.push(`${fileName}: <style> tags are not allowed.`);
  }

  return errors;
}

export function validatePosterTsxFile(
  name: string,
  code: string,
): PosterSingleFileValidationResult {
  const normalizedName = normalizePosterFileName(name);
  const meta = parsePosterMetaFromName(normalizedName);
  const errors: string[] = [];

  if (!meta) {
    errors.push(`${normalizedName}: invalid file naming pattern.`);
  }

  if (!code.trim()) {
    errors.push(`${normalizedName}: file content is empty.`);
  }

  errors.push(...validateTsxComponentShape(normalizedName, code));

  if (meta && !hasDimensionValue(code, "width", meta.width)) {
    errors.push(`${normalizedName}: missing width ${meta.width} in inline style.`);
  }

  if (meta && !hasDimensionValue(code, "height", meta.height)) {
    errors.push(`${normalizedName}: missing height ${meta.height} in inline style.`);
  }

  return {
    ok: errors.length === 0,
    errors,
    fileName: normalizedName,
    file: errors.length === 0 ? code : null,
    meta,
  };
}

export function extractPosterTemplateIdFromFilename(
  name: string,
): PosterSizeId | null {
  const meta = parsePosterMetaFromName(name);
  return meta?.size ?? null;
}

export function validatePosterTsxFiles(
  filesInput: Record<string, string>,
  options?: {
    mode?: PosterGenerationMode;
  },
): PosterValidationResult {
  const files: Record<string, string> = {};
  for (const [name, code] of Object.entries(filesInput)) {
    files[normalizePosterFileName(name)] = code;
  }

  const expectedFileNames = getExpectedPosterFileNames(options?.mode ?? "auto");
  const expected = new Set(expectedFileNames);
  const actualNames = Object.keys(files);

  const missingFiles = expectedFileNames.filter((name) => !(name in files));
  const extraFiles = actualNames.filter((name) => !expected.has(name));

  const errors: string[] = [];
  if (missingFiles.length > 0) {
    errors.push(`Missing files: ${missingFiles.join(", ")}`);
  }
  if (extraFiles.length > 0) {
    errors.push(`Unexpected files: ${extraFiles.join(", ")}`);
  }

  const metadata: Record<string, PosterFileMeta> = {};

  for (const name of expectedFileNames) {
    const code = files[name];
    if (!code) continue;

    const meta = parsePosterMetaFromName(name);
    if (!meta) {
      errors.push(`${name}: invalid file naming pattern.`);
      continue;
    }

    metadata[name] = meta;

    if (!code.trim()) {
      errors.push(`${name}: file content is empty.`);
      continue;
    }

    errors.push(...validateTsxComponentShape(name, code));

    if (!hasDimensionValue(code, "width", meta.width)) {
      errors.push(`${name}: missing width ${meta.width} in inline style.`);
    }

    if (!hasDimensionValue(code, "height", meta.height)) {
      errors.push(`${name}: missing height ${meta.height} in inline style.`);
    }
  }

  return {
    ok: errors.length === 0,
    errors,
    missingFiles,
    extraFiles,
    files,
    metadata,
  };
}

export function sortPosterFiles(
  files: Record<string, string>,
): Array<[string, string]> {
  const normalized = Object.fromEntries(
    Object.entries(files).map(([name, code]) => [normalizePosterFileName(name), code]),
  );

  const ordered: Array<[string, string]> = [];
  for (const name of EXPECTED_POSTER_FILENAMES) {
    if (normalized[name]) {
      ordered.push([name, normalized[name]]);
    }
  }

  for (const [name, code] of Object.entries(normalized)) {
    if (!EXPECTED_POSTER_FILENAMES.includes(name)) {
      ordered.push([name, code]);
    }
  }

  return ordered;
}
