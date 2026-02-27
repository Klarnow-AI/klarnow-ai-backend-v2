export type DesignSystemKey =
  | "minimal"
  | "dark"
  | "playful"
  | "corporate"
  | "luxury"
  | "vibrant";

export type DesignSystem = {
  name: string;
  description: string;
  preview: string;
  dot: string;
  tokens: string;
};

export const designSystems: Record<DesignSystemKey, DesignSystem> = {
  minimal: {
    name: "Clean & Minimal",
    description: "White, lots of space, subtle",
    preview: "bg-white border border-gray-200",
    dot: "bg-blue-600",
    tokens: `
      - Background: white with light gray sections
      - Primary color: blue-600
      - Typography: font-sans, thin weights
      - Corners: rounded-lg
      - Shadows: shadow-sm only
      - Spacing: very generous whitespace
      - Inspired by: Linear.app, Stripe.com
    `,
  },
  dark: {
    name: "Bold & Dark",
    description: "Dark background, high contrast",
    preview: "bg-gray-950 border border-gray-800",
    dot: "bg-violet-500",
    tokens: `
      - Background: #0a0a0a or #111
      - Primary color: violet-500 or user brand color
      - Typography:  font-[600], large sizes
      - Corners: rounded-xl
      - Shadows: shadow-2xl with color glow
      - Inspired by: Vercel.com, Raycast.com
    `,
  },
  playful: {
    name: "Soft & Playful",
    description: "Pastels, rounded, friendly",
    preview: "bg-rose-50 border border-pink-200",
    dot: "bg-pink-500",
    tokens: `
      - Background: soft pastel (rose-50, purple-50)
      - Primary color: pink-500 or purple-500
      - Typography: font-medium, friendly sizes
      - Corners: rounded-3xl everywhere
      - Shadows: shadow-lg colored
      - Inspired by: Notion, Linear onboarding
    `,
  },
  corporate: {
    name: "Corporate & Trust",
    description: "Professional, navy, structured",
    preview: "bg-slate-900 border border-slate-700",
    dot: "bg-blue-400",
    tokens: `
      - Background: white with navy accents
      - Primary color: blue-800 or slate-800
      - Typography: font-semibold, conservative
      - Corners: rounded-md
      - Shadows: shadow-md
      - Trust signals: stats, logos, testimonials
      - Inspired by: Salesforce, HubSpot, IBM
    `,
  },
  luxury: {
    name: "Luxury & Premium",
    description: "Dark, gold accents, elegant",
    preview: "bg-black border border-yellow-900",
    dot: "bg-yellow-400",
    tokens: `
      - Background: #000 or #0a0a0a
      - Primary color: yellow-400 or amber-300 (gold)
      - Typography: elegant, spaced tracking-wide
      - Corners: rounded-none or rounded-sm
      - Shadows: subtle, no heavy shadows
      - Inspired by: luxury fashion brands, Rolls Royce
    `,
  },
  vibrant: {
    name: "Vibrant & Creative",
    description: "Colorful gradients, energetic",
    preview: "bg-gradient-to-br from-purple-600 to-pink-500",
    dot: "bg-white",
    tokens: `
      - Background: bold gradients purple→pink or blue→cyan
      - Primary color: derived from gradient
      - Typography: font-black, expressive
      - Corners: rounded-2xl
      - Shadows: shadow-xl with color
      - Inspired by: Figma, Dribbble, creative agencies
    `,
  },
};
