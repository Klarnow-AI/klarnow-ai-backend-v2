import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import { NextRequest } from "next/server";
import type { BrandContext } from "@/app/api/generate/route";

const MAX_REFERENCE_IMAGES = 3;
const MAX_REFERENCE_IMAGE_BYTES = 4 * 1024 * 1024;
const MAX_MODEL_IMAGE_PARTS = 3;
const POSTER_MAX_OUTPUT_TOKENS = Number.isFinite(
  Number.parseInt(process.env.POSTER_MAX_OUTPUT_TOKENS ?? "16384", 10),
)
  ? Math.max(
      4096,
      Math.min(
        20000,
        Number.parseInt(process.env.POSTER_MAX_OUTPUT_TOKENS ?? "16384", 10),
      ),
    )
  : 16384;
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function buildBrandSection(brand: BrandContext): string {
  const sections: string[] = [];

  const identity: string[] = [];
  if (brand.brandName) identity.push(`Brand name: ${brand.brandName}`);
  if (brand.industry) identity.push(`Industry: ${brand.industry}`);
  if (brand.logoUrl)
    identity.push(`Logo URL (use in an <img> tag): ${brand.logoUrl}`);
  if (brand.colorPalette) {
    const colors = Object.entries(brand.colorPalette)
      .filter(([, v]) => v)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
    if (colors) identity.push(`Brand colors: ${colors}`);
  }
  if (brand.fonts?.length) identity.push(`Fonts: ${brand.fonts.join(", ")}`);
  if (identity.length) sections.push(`BRAND IDENTITY:\n${identity.join("\n")}`);

  const messaging: string[] = [];
  if (brand.coreOffer) messaging.push(`Core offer: ${brand.coreOffer}`);
  if (brand.primaryCta) messaging.push(`Primary CTA: ${brand.primaryCta}`);
  if (brand.elevatorPitch)
    messaging.push(`Elevator pitch: ${brand.elevatorPitch}`);
  if (brand.uspStatement) messaging.push(`USP: ${brand.uspStatement}`);
  if (brand.uspProof) messaging.push(`USP proof: ${brand.uspProof}`);
  if (brand.primaryPain)
    messaging.push(`Customer pain point: ${brand.primaryPain}`);
  if (brand.primaryOutcome)
    messaging.push(`Desired outcome: ${brand.primaryOutcome}`);
  if (brand.heroAngle) messaging.push(`Hero angle: ${brand.heroAngle}`);
  if (messaging.length)
    sections.push(`MESSAGING & COPY:\n${messaging.join("\n")}`);

  if (brand.audiencePersonas?.length) {
    const personas = brand.audiencePersonas
      .map((p) => {
        const parts = [`Persona: ${p.persona}`];
        if (p.needs.length) parts.push(`  Needs: ${p.needs.join(", ")}`);
        if (p.painPoints.length)
          parts.push(`  Pain points: ${p.painPoints.join(", ")}`);
        return parts.join("\n");
      })
      .join("\n");
    sections.push(`TARGET AUDIENCE:\n${personas}`);
  }

  const style: string[] = [];
  if (brand.voiceArchetype)
    style.push(`Voice archetype: ${brand.voiceArchetype}`);
  if (brand.designCues?.length)
    style.push(`Design cues: ${brand.designCues.join(", ")}`);
  if (style.length) sections.push(`VOICE & STYLE:\n${style.join("\n")}`);

  return sections.length > 0
    ? `\n\nBRAND CONTEXT:\n${sections.join("\n\n")}`
    : "";
}

function buildSystemPrompt(brandContext?: BrandContext): string {
  const brandSection = brandContext ? buildBrandSection(brandContext) : "";
  const brandName = brandContext?.brandName;

  return `# POSTER GENERATOR SYSTEM PROMPT (V3)

## Campaign Designer Mode (2026) - Multi-Size Default

You are an award-winning campaign designer and direct-response copywriter with 25 years of experience creating high-converting posters, billboards, and OOH creatives.

Your job is to create posters that grab attention, connect to a real buyer problem, and drive one clear action. Prioritize clarity, legibility, and conversion over decoration.

INPUTS YOU RECEIVE
1. messages: chat history (user + assistant)
2. brandContext (optional object)

MODE SELECTION (IMPORTANT)

Mode 1 (asking):
- If you do not have enough context to design a converting poster, ask ONLY 1 or 2 short questions, then stop.
- Ask about:
1. Poster purpose and desired action (one action only)
2. Preferred visual style (choose from 3 to 5 options)
- Do not generate code in Mode 1.

Mode 2 (generating):
- If enough context exists, generate one <summary> block and sixteen TSX files.
- Do not ask questions in Mode 2.

WHAT COUNTS AS ENOUGH CONTEXT
- Who the poster is for (audience or persona)
- What is being sold (offer)
- What action they should take (CTA)
- If any are missing, use Mode 1.

NON-NEGOTIABLE OOH RULES
- 3-second rule: message must be understood fast.
- One poster equals one idea.
- Headline must be 3 to 7 words, unless deliberately a big type wall that still reads instantly.
- Use plain language. No jargon. No fake hype.
- Claims must be believable. Add proof or specificity when possible.
- One primary CTA only.
- Legibility first. High contrast, large type, strong hierarchy.
- Avoid em dashes. Use full stops or commas.

DESIGN STYLE TARGET
- Bold minimal layouts with negative space
- Smart typography with strong hierarchy
- Occasional pattern interrupt
- Premium feel, not generic marketing flyer

COPY RULES
- Headline must sound like a real person.
- Prefer short words and clean punctuation.
- Avoid: revolutionary, game-changer, world-class, unlock, synergy.
- Use one device when it helps: brutal truth, clever twist, or proof-led confidence.
- Match voiceArchetype when provided.
- Respect designCues as constraints.

BRAND RULES
${brandName ? `- Brand name is "${brandName}". Never use placeholder brand names.` : "- Use brand name from provided context when available."}
${brandContext?.logoUrl ? `- logoUrl is "${brandContext.logoUrl}". Use it subtly when suitable.` : "- If no logoUrl exists, use brandName as a text-based mark."}
${
  brandContext?.colorPalette
    ? `- Use brandContext color palette as primary direction: ${Object.entries(
        brandContext.colorPalette,
      )
        .filter(([, v]) => v)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ")}.`
    : "- If palette is missing, choose a clean modern palette with neutral base and one accent."
}
- Do not use neon or electric glow unless the palette clearly calls for it.

MULTI-SIZE REQUIREMENT (MANDATORY)
For every concept, produce FOUR size-specific layouts:
1. 4x5 Feed: 1080 x 1350
2. 9x16 Story: 1080 x 1920
3. 16x9 Landscape: 1920 x 1080
4. 1x1 Square: 1080 x 1080

Do not stretch one layout across sizes. Re-layout each size for legibility and balance.

SAFE ZONES
- 9x16 Story: keep critical text away from top 200px and bottom 260px.
- 4x5 and 1x1: use generous margins.
- 16x9: prioritize horizontal reading flow and avoid tiny text.

OUTPUT REQUIREMENTS (Mode 2)
Return exactly:
1. <summary>...</summary>
2. Sixteen TSX files with these exact names:
- /poster-v1-4x5.tsx
- /poster-v1-9x16.tsx
- /poster-v1-16x9.tsx
- /poster-v1-1x1.tsx
- /poster-v2-4x5.tsx
- /poster-v2-9x16.tsx
- /poster-v2-16x9.tsx
- /poster-v2-1x1.tsx
- /poster-v3-4x5.tsx
- /poster-v3-9x16.tsx
- /poster-v3-16x9.tsx
- /poster-v3-1x1.tsx
- /poster-v4-4x5.tsx
- /poster-v4-9x16.tsx
- /poster-v4-16x9.tsx
- /poster-v4-1x1.tsx

SUMMARY FORMAT (SHORT)
Inside <summary>, include:
- Audience insight (2 to 4 bullets)
- Single-minded promise (1 sentence)
- CTA (exact text)
- 3-second test (pass/fail with one fix if fail)
- One line on V1, V2, V3, V4 differences

TSX SPEC (CRITICAL)
Each file must be a complete self-contained TSX component:
- No imports.
- Use export default function ComponentName() { ... }.
- Inline styles only with style={{ ... }} objects.
- No className usage.
- No external CSS, no style tags, no external libraries.
- Use a fixed poster artboard root div matching the file size.
- Use accessible contrast and large type.
- Include CTA and brand mark consistently.
- Optional QR placeholder block is allowed.
- If no logo image exists, use tasteful abstract shape or placeholder block.

VARIATION REQUIREMENTS
1. Variant 1: Brutal truth
2. Variant 2: Clever twist
3. Variant 3: Proof-led
4. Variant 4: Editorial premium

MODE 1 QUESTION TEMPLATE (USE EXACTLY, KEEP SHORT)
Q1: "What is this poster trying to make people do? (Pick one: book a call, buy now, sign up, visit site, call, DM)"
Q2: "Pick a visual style: Minimal bold type, Editorial premium, Playful meta, Photo-led, or Dark high-contrast."

DO NOT
- Do not output markdown.
- Do not output explanations outside <summary> and <file> tags.
- Do not add extra files beyond the 16 TSX files.
- Do not ask more than 2 questions in Mode 1.

When in Mode 2, output only <summary> and <file> tags.
${brandSection}`;
}

type ChatMessage = { role: string; content: string };

type ReferenceImageInput = {
  name: string;
  mimeType: string;
  dataUrl: string;
};

type ValidReferenceImage = {
  name: string;
  mimeType: string;
  dataUrl: string;
  base64Data: string;
};

type RetrievedImageContextItem = {
  preview_url?: string | null;
};

type RetrievedImageContextResponse = {
  context_text?: string | null;
  items?: RetrievedImageContextItem[] | null;
};

type RetrievedImageContext = {
  contextText: string | null;
  imageUrls: string[];
};

const DATA_URL_PATTERN = /^data:([a-zA-Z0-9./+\-]+);base64,([A-Za-z0-9+/=]+)$/;

function estimateBase64Bytes(base64Data: string): number {
  const padding = base64Data.endsWith("==") ? 2 : base64Data.endsWith("=") ? 1 : 0;
  return Math.floor((base64Data.length * 3) / 4) - padding;
}

function normalizeMessages(raw: unknown): ChatMessage[] | null {
  if (!Array.isArray(raw)) return null;
  const messages: ChatMessage[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") return null;
    const role = (item as { role?: unknown }).role;
    const content = (item as { content?: unknown }).content;
    if (typeof role !== "string" || typeof content !== "string") return null;
    if (!["user", "assistant", "system"].includes(role)) return null;
    messages.push({ role, content });
  }
  return messages;
}

function normalizeReferenceImages(
  raw: unknown,
): { images: ValidReferenceImage[]; error: string | null } {
  if (raw == null) return { images: [], error: null };
  if (!Array.isArray(raw)) {
    return {
      images: [],
      error:
        "referenceImages must be an array of { name, mimeType, dataUrl }.",
    };
  }
  if (raw.length > MAX_REFERENCE_IMAGES) {
    return {
      images: [],
      error: `You can attach up to ${MAX_REFERENCE_IMAGES} reference images.`,
    };
  }

  const parsed: ValidReferenceImage[] = [];
  for (let index = 0; index < raw.length; index += 1) {
    const item = raw[index];
    if (!item || typeof item !== "object") {
      return { images: [], error: `referenceImages[${index}] is invalid.` };
    }
    const name = (item as { name?: unknown }).name;
    const mimeType = (item as { mimeType?: unknown }).mimeType;
    const dataUrl = (item as { dataUrl?: unknown }).dataUrl;

    if (
      typeof name !== "string" ||
      typeof mimeType !== "string" ||
      typeof dataUrl !== "string"
    ) {
      return {
        images: [],
        error: `referenceImages[${index}] must include name, mimeType, and dataUrl strings.`,
      };
    }

    if (!mimeType.toLowerCase().startsWith("image/")) {
      return {
        images: [],
        error: `referenceImages[${index}] must be an image mime type.`,
      };
    }

    const match = DATA_URL_PATTERN.exec(dataUrl.trim());
    if (!match) {
      return {
        images: [],
        error: `referenceImages[${index}] has an invalid dataUrl format.`,
      };
    }

    const dataUrlMime = match[1].toLowerCase();
    const base64Data = match[2];
    if (!dataUrlMime.startsWith("image/")) {
      return {
        images: [],
        error: `referenceImages[${index}] dataUrl must be an image.`,
      };
    }

    const sizeBytes = estimateBase64Bytes(base64Data);
    if (sizeBytes > MAX_REFERENCE_IMAGE_BYTES) {
      return {
        images: [],
        error: `referenceImages[${index}] is larger than 4MB.`,
      };
    }

    parsed.push({
      name: name.trim() || `image-${index + 1}`,
      mimeType: dataUrlMime,
      dataUrl: dataUrl.trim(),
      base64Data,
    });
  }

  return { images: parsed, error: null };
}

function normalizePackId(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  return UUID_PATTERN.test(trimmed) ? trimmed : null;
}

function mergeImageUrls(
  dataUrlImages: ValidReferenceImage[],
  retrievedImageUrls: string[],
): string[] {
  const merged: string[] = [];
  for (const image of dataUrlImages) {
    if (!image.dataUrl || merged.includes(image.dataUrl)) continue;
    merged.push(image.dataUrl);
    if (merged.length >= MAX_MODEL_IMAGE_PARTS) return merged;
  }
  for (const url of retrievedImageUrls) {
    if (!url || merged.includes(url)) continue;
    merged.push(url);
    if (merged.length >= MAX_MODEL_IMAGE_PARTS) return merged;
  }
  return merged;
}

function appendRetrievedContextToLatestUserMessage(
  messages: ChatMessage[],
  contextText: string | null,
): ChatMessage[] {
  if (!contextText || !contextText.trim()) return messages;
  const latestUserIndex = findLatestUserMessageIndex(messages);
  if (latestUserIndex < 0) return messages;

  return messages.map((message, index) => {
    if (index !== latestUserIndex) return message;
    const base = (message.content || "").trim();
    const context = contextText.trim();
    const merged = base
      ? `${base}\n\nGlobal image library context:\n${context}`
      : `Global image library context:\n${context}`;
    return { ...message, content: merged };
  });
}

async function fetchGlobalPosterImageContext(options: {
  query: string;
  authorizationHeader: string | null;
}): Promise<RetrievedImageContext> {
  const backendBase =
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";
  const url = `${backendBase}/api/v1/image-context/global/retrieve`;

  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (options.authorizationHeader) {
      headers.Authorization = options.authorizationHeader;
    }

    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        query: options.query,
        top_k: MAX_MODEL_IMAGE_PARTS,
      }),
    });
    if (!res.ok) {
      return { contextText: null, imageUrls: [] };
    }

    const payload = (await res.json()) as RetrievedImageContextResponse;
    const contextText =
      typeof payload.context_text === "string" ? payload.context_text : null;
    const imageUrls = Array.isArray(payload.items)
      ? payload.items
          .map((item) =>
            typeof item?.preview_url === "string" ? item.preview_url : null,
          )
          .filter((url): url is string => Boolean(url))
          .slice(0, MAX_MODEL_IMAGE_PARTS)
      : [];

    return { contextText, imageUrls };
  } catch {
    return { contextText: null, imageUrls: [] };
  }
}

function findLatestUserMessageIndex(messages: ChatMessage[]): number {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === "user") return index;
  }
  return -1;
}

function buildAnthropicMessages(
  messages: ChatMessage[],
  referenceImages: ValidReferenceImage[],
): Array<Record<string, unknown>> {
  if (referenceImages.length === 0) {
    return messages.map((message) => ({
      role: message.role === "system" ? "assistant" : message.role,
      content: message.content,
    }));
  }

  const latestUserIndex = findLatestUserMessageIndex(messages);
  return messages.map((message, index) => {
    const role = message.role === "system" ? "assistant" : message.role;
    if (role !== "user" || index !== latestUserIndex) {
      return { role, content: message.content };
    }

    const contentBlocks: Array<Record<string, unknown>> = [
      {
        type: "text",
        text: message.content || "Use the attached reference images as context.",
      },
    ];

    for (const image of referenceImages) {
      contentBlocks.push({
        type: "image",
        source: {
          type: "base64",
          media_type: image.mimeType,
          data: image.base64Data,
        },
      });
    }

    return { role, content: contentBlocks };
  });
}

function buildOpenAiMessages(
  messages: ChatMessage[],
  referenceImages: ValidReferenceImage[],
  retrievedImageUrls: string[],
): Array<Record<string, unknown>> {
  const mergedImageUrls = mergeImageUrls(referenceImages, retrievedImageUrls);
  if (mergedImageUrls.length === 0) {
    return messages.map((message) => ({
      role: message.role,
      content: message.content,
    }));
  }

  const latestUserIndex = findLatestUserMessageIndex(messages);
  return messages.map((message, index) => {
    if (message.role !== "user" || index !== latestUserIndex) {
      return { role: message.role, content: message.content };
    }

    const contentParts: Array<Record<string, unknown>> = [
      {
        type: "text",
        text: message.content || "Use the attached reference images as context.",
      },
    ];

    for (const url of mergedImageUrls) {
      contentParts.push({
        type: "image_url",
        image_url: {
          url,
        },
      });
    }

    return {
      role: message.role,
      content: contentParts,
    };
  });
}

function streamWithAnthropic(
  anthropic: Anthropic,
  systemPrompt: string,
  messages: ChatMessage[],
  referenceImages: ValidReferenceImage[],
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const anthropicMessages = buildAnthropicMessages(messages, referenceImages);

  return new ReadableStream({
    async start(controller) {
      const stream = anthropic.messages.stream({
        model: "claude-sonnet-4-6",
        max_tokens: POSTER_MAX_OUTPUT_TOKENS,
        system: systemPrompt,
        messages: anthropicMessages as never,
      });

      for await (const event of stream) {
        if (
          event.type === "content_block_delta" &&
          event.delta.type === "text_delta"
        ) {
          controller.enqueue(encoder.encode(event.delta.text));
        }
      }
      controller.close();
    },
  });
}

function streamWithOpenAI(
  openai: OpenAI,
  systemPrompt: string,
  messages: ChatMessage[],
  referenceImages: ValidReferenceImage[],
  retrievedImageUrls: string[],
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const openAiMessages = buildOpenAiMessages(
    messages,
    referenceImages,
    retrievedImageUrls,
  );

  return new ReadableStream({
    async start(controller) {
      const stream = await openai.chat.completions.create({
        model: "gpt-4o",
        max_tokens: POSTER_MAX_OUTPUT_TOKENS,
        stream: true,
        messages: [
          { role: "system", content: systemPrompt },
          ...openAiMessages,
        ] as never,
      });

      for await (const chunk of stream) {
        const delta = chunk.choices[0]?.delta?.content;
        if (delta) {
          controller.enqueue(encoder.encode(delta));
        }
      }
      controller.close();
    },
  });
}

async function createPassthroughStream(
  readable: ReadableStream<Uint8Array>,
): Promise<ReadableStream<Uint8Array>> {
  const reader = readable.getReader();
  const firstChunk = await reader.read();

  return new ReadableStream<Uint8Array>({
    async start(controller) {
      if (firstChunk.value) controller.enqueue(firstChunk.value);
      if (firstChunk.done) {
        controller.close();
        return;
      }
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          controller.enqueue(value);
        }
        controller.close();
      } catch (err) {
        controller.error(err);
      }
    },
  });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const messages = normalizeMessages(body.messages);
    const brandContext = body.brandContext as BrandContext | undefined;
    const {
      images: referenceImages,
      error: referenceImageError,
    } = normalizeReferenceImages(body.referenceImages as ReferenceImageInput[] | undefined);

    if (!messages || messages.length === 0) {
      return new Response(JSON.stringify({ error: "Missing messages" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (referenceImageError) {
      return new Response(JSON.stringify({ error: referenceImageError }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const packId = normalizePackId(body.packId);
    if (body.packId != null && !packId) {
      return new Response(JSON.stringify({ error: "Invalid packId" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    let messagesForGeneration = messages;
    let retrievedImageUrls: string[] = [];
    const imageContextPosterEnabled =
      (process.env.IMAGE_CONTEXT_POSTER_ENABLED ?? "true").toLowerCase() !==
      "false";
    if (imageContextPosterEnabled) {
      const latestUserIndex = findLatestUserMessageIndex(messages);
      const latestUserContent =
        latestUserIndex >= 0 ? messages[latestUserIndex].content : "";
      if (latestUserContent.trim()) {
        const retrieval = await fetchGlobalPosterImageContext({
          query: latestUserContent,
          authorizationHeader: req.headers.get("authorization"),
        });
        messagesForGeneration = appendRetrievedContextToLatestUserMessage(
          messagesForGeneration,
          retrieval.contextText,
        );
        retrievedImageUrls = retrieval.imageUrls;
      }
    }

    const hasAnthropic = !!process.env.ANTHROPIC_API_KEY?.trim();
    const hasOpenAI = !!process.env.OPENAI_API_KEY?.trim();
    if (!hasAnthropic && !hasOpenAI) {
      return new Response(
        JSON.stringify({
          error:
            "Generate not configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in the server environment.",
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      );
    }

    const systemPrompt = buildSystemPrompt(brandContext);

    const anthropic = hasAnthropic
      ? new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
      : null;
    const openai = hasOpenAI
      ? new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
      : null;

    let readable: ReadableStream<Uint8Array>;

    if (anthropic) {
      try {
        readable = await createPassthroughStream(
          streamWithAnthropic(
            anthropic,
            systemPrompt,
            messagesForGeneration,
            referenceImages,
          ),
        );
      } catch (anthropicError) {
        console.error(
          "Anthropic failed, falling back to OpenAI:",
          anthropicError,
        );
        if (!openai) {
          return new Response(
            JSON.stringify({
              error:
                "We're having trouble generating right now. Please try again in a few moments.",
            }),
            {
              status: 503,
              headers: { "Content-Type": "application/json" },
            },
          );
        }
        try {
          readable = await createPassthroughStream(
            streamWithOpenAI(
              openai,
              systemPrompt,
              messagesForGeneration,
              referenceImages,
              retrievedImageUrls,
            ),
          );
        } catch (openaiError) {
          console.error(
            "OpenAI fallback failed (both providers failed):",
            openaiError,
          );
          return new Response(
            JSON.stringify({
              error:
                "We're having trouble generating right now. Please try again in a few moments.",
            }),
            {
              status: 503,
              headers: { "Content-Type": "application/json" },
            },
          );
        }
      }
    } else {
      try {
        readable = await createPassthroughStream(
          streamWithOpenAI(
            openai!,
            systemPrompt,
            messagesForGeneration,
            referenceImages,
            retrievedImageUrls,
          ),
        );
      } catch (openaiError) {
        console.error("OpenAI generation failed:", openaiError);
        return new Response(
          JSON.stringify({
            error:
              "We're having trouble generating right now. Please try again in a few moments.",
          }),
          {
            status: 503,
            headers: { "Content-Type": "application/json" },
          },
        );
      }
    }

    return new Response(readable, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Transfer-Encoding": "chunked",
      },
    });
  } catch (error) {
    console.error("Generate poster API error:", error);
    return new Response(JSON.stringify({ error: "Internal server error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
