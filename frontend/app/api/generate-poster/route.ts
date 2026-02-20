import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import { NextRequest } from "next/server";
import type { BrandContext } from "@/app/api/generate/route";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

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
  if (identity.length)
    sections.push(`BRAND IDENTITY:\n${identity.join("\n")}`);

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
    ? `- Use these brand colors as the dominant palette: ${Object.entries(brandContext.colorPalette)
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
- You may output multiple <file> tags if the user asks for variations
- When generating, do NOT write ANY text outside <summary> and <file> tags — no markdown, no explanations
${brandSection}`;
}

type ChatMessage = { role: string; content: string };

function streamWithAnthropic(
  systemPrompt: string,
  messages: ChatMessage[]
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream({
    async start(controller) {
      const stream = anthropic.messages.stream({
        model: "claude-sonnet-4-6",
        max_tokens: 8192,
        system: systemPrompt,
        messages: messages.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        })),
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
  systemPrompt: string,
  messages: ChatMessage[]
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream({
    async start(controller) {
      const stream = await openai.chat.completions.create({
        model: "gpt-4o",
        max_tokens: 8192,
        stream: true,
        messages: [
          { role: "system", content: systemPrompt },
          ...messages.map((m) => ({
            role: m.role as "user" | "assistant",
            content: m.content,
          })),
        ],
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

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages, brandContext } = body;

    if (!messages) {
      return new Response(
        JSON.stringify({ error: "Missing messages" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    const systemPrompt = buildSystemPrompt(brandContext);

    let readable: ReadableStream<Uint8Array>;
    try {
      readable = streamWithAnthropic(systemPrompt, messages);
      const reader = readable.getReader();
      const firstChunk = await reader.read();

      const passthrough = new ReadableStream<Uint8Array>({
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

      readable = passthrough;
    } catch (anthropicError) {
      console.error(
        "Anthropic failed, falling back to OpenAI:",
        anthropicError
      );
      readable = streamWithOpenAI(systemPrompt, messages);
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
