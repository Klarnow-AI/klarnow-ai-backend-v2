import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import { NextRequest } from "next/server";
import type { BrandContext } from "@/app/api/generate/route";

const MAX_REFERENCE_IMAGES = 3;
const MAX_REFERENCE_IMAGE_BYTES = 4 * 1024 * 1024;
const MAX_MODEL_IMAGE_PARTS = 3;
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

  return `You are an expert graphic designer AI that creates stunning posters and flyers as self-contained HTML with inline styles only. Each design must be visually striking, print-ready, and brand-consistent.

POSTER CANVAS — CRITICAL RULES:
- Every poster MUST have a single root <div> as the outermost element with EXACTLY:
  style="width:600px;height:850px;position:relative;overflow:hidden;box-sizing:border-box;[plus background/font styles]"
- Root div dimensions: width 600px, height 850px — NO exceptions, NO other sizes
- Use ONLY inline styles on EVERY element — ZERO CSS classes, ZERO Tailwind, ZERO external stylesheets, ZERO <style> tags
- Use ONLY web-safe / system fonts: Arial, Helvetica, Georgia, 'Times New Roman', Verdana, Courier New, or system-ui
- All colors must be hex values (e.g. #1a1a2e) — no rgb(), no named colors
- All sizes in px — no em, rem, %, vw, vh

TWO RESPONSE MODES:

Mode 1 — ASKING (first message, not enough design info):
- Ask 1-2 short clarifying questions about the poster's purpose and preferred visual style
- Response is plain conversational text only — NO <file> or <summary> tags, NO code

Mode 2 — GENERATING (when you have enough context to make a specific design):
- Output ONLY the <summary> and <file> tags — nothing else

Do NOT generate code until you have enough context for a specific, on-brand design.

DESIGN PRINCIPLES:
- Bold typography with clear visual hierarchy: large headline → supporting text → CTA
- Eye-catching background using inline gradient or solid color
- Use geometric shapes / decorative elements via absolutely positioned divs with border-radius
- Include a clear, prominent call-to-action section
- Layer content using position:absolute for visual depth
- All text must have strong contrast against its background
${brandName ? `- Brand name is "${brandName}" — NEVER use placeholder text` : ""}
${brandContext?.logoUrl ? `- Include the logo using: <img src="${brandContext.logoUrl}" alt="${brandName}" style="..." />` : ""}
${
  brandContext?.colorPalette
    ? `- Use these brand colors as the dominant palette: ${Object.entries(
        brandContext.colorPalette,
      )
        .filter(([, v]) => v)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ")}`
    : "- Choose a bold, cohesive color palette that fits the brand and industry"
}

INLINE STYLE CHEATSHEET (html2canvas requires ALL styles to be inline):
- Background gradient: style="background:linear-gradient(135deg,#color1 0%,#color2 100%)"
- Centered flex column: style="display:flex;flex-direction:column;align-items:center;justify-content:center"
- Absolute element: style="position:absolute;top:Xpx;left:Xpx;width:Xpx;height:Xpx"
- Text: style="font-family:Arial,sans-serif;font-size:48px;font-weight:700;color:#ffffff;line-height:1.1"
- Circle shape: style="position:absolute;border-radius:50%;background:#color;width:Xpx;height:Xpx"
- Semi-transparent overlay: style="position:absolute;inset:0;background:rgba(0,0,0,0.35)"

LAYOUT PATTERN (use as a guide):
- Full-bleed background: the root div itself has the main background
- Decorative circles/shapes: position:absolute elements for visual interest
- Content stack: a flex column positioned in the main content area
- Logo area (if available): top 60px, centered
- Headline: bold, 40-56px, centered or left-aligned
- Subheadline / body: 16-20px, lighter weight
- CTA button: inline-block styled div, contrasting color, rounded corners via border-radius
- Footer strip: position:absolute, bottom:0, full-width band for contact / tagline

OUTPUT FORMAT (Mode 2 only):
<summary>One sentence describing what was created.</summary>
<file name="/DescriptivePosterName.html">
<div style="width:600px;height:850px;position:relative;overflow:hidden;box-sizing:border-box;background:linear-gradient(...);">
  <!-- all poster content here using inline styles only -->
</div>
</file>

- File name must end in .html and describe the design (e.g. /SummerPromoFlyer.html, /EventAnnouncement.html)
- ALWAYS output exactly 4 <file> tags with distinct design variations (different layouts, color schemes, or visual styles). Each variation should be a unique interpretation of the request.
- When generating, do NOT write ANY text outside <summary> and <file> tags — no markdown, no explanations
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
      ? `${base}\n\nPack image library context:\n${context}`
      : `Pack image library context:\n${context}`;
    return { ...message, content: merged };
  });
}

async function fetchPosterImageContext(options: {
  packId: string;
  query: string;
  authorizationHeader: string | null;
}): Promise<RetrievedImageContext> {
  if (!options.authorizationHeader) {
    return { contextText: null, imageUrls: [] };
  }

  const backendBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${backendBase}/api/v1/image-context/packs/${options.packId}/retrieve`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: options.authorizationHeader,
      },
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
        max_tokens: 8192,
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
        max_tokens: 8192,
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
    const packId = normalizePackId(body.packId);
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
    if (packId && imageContextPosterEnabled) {
      const latestUserIndex = findLatestUserMessageIndex(messages);
      const latestUserContent =
        latestUserIndex >= 0 ? messages[latestUserIndex].content : "";
      if (latestUserContent.trim()) {
        const retrieval = await fetchPosterImageContext({
          packId,
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
