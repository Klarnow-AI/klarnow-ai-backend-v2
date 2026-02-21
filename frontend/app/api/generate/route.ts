import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import { NextRequest } from "next/server";
import { designSystems, type DesignSystemKey } from "@/lib/designSystems";

export type BrandContext = {
  brandName?: string;
  coreOffer?: string;
  primaryCta?: string;
  primaryPain?: string;
  primaryOutcome?: string;
  heroAngle?: string;
  uspStatement?: string;
  uspProof?: string;
  logoUrl?: string;
  colorPalette?: { primary?: string; secondary?: string; accent?: string };
  fonts?: string[];
  mission?: string;
  vision?: string;
  elevatorPitch?: string;
  proofPoints?: string[];
  audiencePersonas?: Array<{
    persona: string;
    needs: string[];
    painPoints: string[];
  }>;
  voiceArchetype?: string;
  designCues?: string[];
  industry?: string;
};

type ChatMessage = { role: string; content: string };

// Model configuration
const GENERATION_MODEL = "claude-opus-4-6";
const EDIT_MODEL = "claude-sonnet-4-6";
const MAX_TOKENS = 20000;
const THINKING_BUDGET_GEN = 10000;
const THINKING_BUDGET_EDIT = 6000;

function isDefaultFiles(files: Record<string, string>): boolean {
  const keys = Object.keys(files);
  if (keys.length !== 1) return false;
  const content = files["/App.tsx"] || files["App.tsx"] || "";
  return content.includes("Describe your website to get started");
}

// ---------------------------------------------------------------------------
// Brand context helpers
// ---------------------------------------------------------------------------

function buildBrandSection(brand: BrandContext): string {
  const sections: string[] = [];

  const identity: string[] = [];
  if (brand.brandName) identity.push(`Brand name: ${brand.brandName}`);
  if (brand.industry) identity.push(`Industry: ${brand.industry}`);
  if (brand.logoUrl) identity.push(`Logo URL (use in an <img> tag): ${brand.logoUrl}`);
  if (brand.colorPalette) {
    const colors = Object.entries(brand.colorPalette)
      .filter(([, v]) => v)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
    if (colors) identity.push(`Brand colors: ${colors}`);
  }
  if (brand.fonts?.length) identity.push(`Preferred fonts: ${brand.fonts.join(", ")}`);
  if (identity.length) sections.push(`BRAND IDENTITY:\n${identity.join("\n")}`);

  const messaging: string[] = [];
  if (brand.coreOffer) messaging.push(`Core offer: ${brand.coreOffer}`);
  if (brand.primaryCta) messaging.push(`Primary CTA text: ${brand.primaryCta}`);
  if (brand.elevatorPitch) messaging.push(`Elevator pitch: ${brand.elevatorPitch}`);
  if (brand.uspStatement) messaging.push(`USP: ${brand.uspStatement}`);
  if (brand.uspProof) messaging.push(`USP proof: ${brand.uspProof}`);
  if (brand.primaryPain) messaging.push(`Customer pain point: ${brand.primaryPain}`);
  if (brand.primaryOutcome) messaging.push(`Desired outcome: ${brand.primaryOutcome}`);
  if (brand.heroAngle) messaging.push(`Hero angle: ${brand.heroAngle}`);
  if (brand.mission) messaging.push(`Mission: ${brand.mission}`);
  if (brand.vision) messaging.push(`Vision: ${brand.vision}`);
  if (brand.proofPoints?.length)
    messaging.push(`Proof points:\n- ${brand.proofPoints.join("\n- ")}`);
  if (messaging.length) sections.push(`MESSAGING & COPY:\n${messaging.join("\n")}`);

  if (brand.audiencePersonas?.length) {
    const personas = brand.audiencePersonas
      .map((p) => {
        const parts = [`Persona: ${p.persona}`];
        if (p.needs.length) parts.push(`  Needs: ${p.needs.join(", ")}`);
        if (p.painPoints.length) parts.push(`  Pain points: ${p.painPoints.join(", ")}`);
        return parts.join("\n");
      })
      .join("\n");
    sections.push(`TARGET AUDIENCE:\n${personas}`);
  }

  const style: string[] = [];
  if (brand.voiceArchetype) style.push(`Voice archetype: ${brand.voiceArchetype}`);
  if (brand.designCues?.length) style.push(`Design cues: ${brand.designCues.join(", ")}`);
  if (style.length) sections.push(`VOICE & STYLE:\n${style.join("\n")}`);

  return sections.length > 0
    ? `\n\nBRAND CONTEXT:\n${sections.join("\n\n")}`
    : "";
}

function buildBrandIntro(brand: BrandContext): string {
  const parts: string[] = [];
  if (brand.brandName) parts.push(`brand: "${brand.brandName}"`);
  if (brand.coreOffer) parts.push(`offer: ${brand.coreOffer}`);
  if (brand.industry) parts.push(`industry: ${brand.industry}`);
  if (brand.elevatorPitch) parts.push(`pitch: "${brand.elevatorPitch}"`);
  if (brand.colorPalette) {
    const colors = Object.entries(brand.colorPalette)
      .filter(([, v]) => v)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
    if (colors) parts.push(`brand colors: ${colors}`);
  }
  if (!parts.length) return "";
  return `\nKNOWN BRAND INFO: ${parts.join("; ")}.`;
}

function buildIndustryTemplate(brand: BrandContext): string {
  const industry = brand.industry?.toLowerCase() ?? "";
  const offer = brand.coreOffer?.toLowerCase() ?? "";
  const combined = `${industry} ${offer}`;

  if (/fitness|gym|health|wellness|yoga|nutrition|personal.?train/.test(combined)) {
    return `
INDUSTRY TEMPLATE — FITNESS/WELLNESS:
Recommended sections in order:
1. Nav: Logo + links (Programs, Results, About, Pricing) + "Book Free Call" CTA
2. Hero: Transformation headline ("Stop struggling with X. Start achieving Y.") + energetic CTA + social proof badge ("500+ clients transformed")
3. Stats Bar: 3-4 numbers — clients, avg results (e.g. "23 lbs avg lost"), rating, years
4. How It Works: 3 steps (Assessment → Custom Plan → Transform) — numbered with icons
5. Features/Programs: What's included in the program/service
6. Testimonials: Real results with SPECIFIC numbers ("Lost 23 lbs in 8 weeks", headshots or initials)
7. About/Credibility: Trainer story, certifications, why you're qualified
8. Pricing/Packages: 2-3 tiers — clear what each includes
9. FAQ: Address objections (time, cost, experience level)
10. Final CTA: Bold section — "Start Your Transformation Today" + free consult offer
COPY TONE: Energetic, empowering, results-focused. Use action verbs. Address excuses.`;
  }

  if (/saas|software|app|platform|api|tool|dashboard|b2b|crm|erp/.test(combined)) {
    return `
INDUSTRY TEMPLATE — SAAS/TECH:
Recommended sections in order:
1. Nav: Logo + links (Features, Pricing, Docs, Blog) + "Start Free Trial" + "Sign In"
2. Hero: Problem-focused headline + product screenshot/mockup (use a styled div) + "Used by X companies"
3. Logos: "Trusted by teams at..." — 5-6 recognizable company logos (styled text placeholders)
4. Features: 3-column icon grid — capabilities, NOT just feature names (use emoji icons ⚡🔒📊)
5. How It Works: 3-step numbered flow with brief explanations
6. Social Proof: 1 large pull quote from a customer + their name/company/role
7. Testimonials: 3 cards — different buyer personas (founder, PM, developer)
8. Pricing: 3 tiers — Starter, Pro (highlighted), Enterprise. Include feature comparison.
9. FAQ: Billing, security, integrations, support
10. Final CTA: "Start your free 14-day trial — no credit card required"
COPY TONE: Clear, confident, metrics-driven. Quantify everything. Address security/trust.`;
  }

  if (/restaurant|food|cafe|bakery|catering|bar|bistro|eatery/.test(combined)) {
    return `
INDUSTRY TEMPLATE — FOOD/HOSPITALITY:
Recommended sections in order:
1. Nav: Logo + (Menu, Reservations, About, Contact) + "Reserve a Table" button
2. Hero: Atmospheric full-height section — restaurant name, tagline, "Book Now" + "View Menu"
3. Featured Dishes: 3-4 signature items with beautiful placeholder cards
4. About/Story: Chef or owner story, philosophy, what makes this place special
5. Experience: Ambiance, atmosphere — describe the dining experience
6. Testimonials: Review quotes (Google/Yelp style) with star ratings and names
7. Hours & Location: Operating hours + address + embedded map placeholder
8. Reservations CTA: "Reserve Your Table" with phone/link
COPY TONE: Warm, inviting, sensory. Use food descriptors. Evoke atmosphere.`;
  }

  if (/agency|marketing|design|creative|consulting|freelance|studio/.test(combined)) {
    return `
INDUSTRY TEMPLATE — AGENCY/SERVICES:
Recommended sections in order:
1. Nav: Logo + (Work, Services, About, Blog) + "Start a Project"
2. Hero: Positioning statement ("We help [audience] achieve [outcome]") + reel/portfolio preview cards
3. Services: 3-4 core services with brief description and what's included
4. Process: 4-step workflow (Discovery → Strategy → Execution → Launch)
5. Case Studies: 2-3 project cards with client name, industry, result achieved
6. Testimonials: Client quotes with name, company, and specific results
7. About: Team introduction or founder story
8. Logos: "Brands we've worked with"
9. Pricing/Packages: Optional — or "Let's talk" CTA
10. Contact CTA: Prominent with form or Calendly-style booking prompt
COPY TONE: Confident, results-oriented, client-focused. Show don't tell.`;
  }

  if (/ecommerce|shop|store|retail|fashion|clothing|product/.test(combined)) {
    return `
INDUSTRY TEMPLATE — E-COMMERCE/RETAIL:
Recommended sections in order:
1. Nav: Logo + (Shop, Collections, About, Contact) + Cart icon + Search
2. Hero: Hero banner with main product/collection — urgency element ("Limited Edition", "New Arrivals")
3. Featured Products: 4-6 product cards in a grid with price, name, quick-add
4. Collections: Category cards linking to different product types
5. Social Proof: UGC-style testimonials + star rating summary ("4.9 stars, 1,200+ reviews")
6. Value Props: Free shipping, easy returns, quality guarantee — icon + text cards
7. About/Brand Story: Why this brand exists, what makes products special
8. Instagram Grid: 6 lifestyle/product images (styled placeholders)
9. Newsletter: Email capture with incentive ("Get 15% off your first order")
COPY TONE: Aspirational, visual, lifestyle-focused. Create desire and urgency.`;
  }

  if (/coach|coaching|mentor|course|training|learn|education|tutor/.test(combined)) {
    return `
INDUSTRY TEMPLATE — COACHING/EDUCATION:
Recommended sections in order:
1. Nav: Logo + (About, Programs, Results, Blog) + "Book Free Call"
2. Hero: Who you help + what transformation you deliver + "Get Started" CTA
3. Authority Signals: Credentials, featured in, certifications, years of experience
4. Who It's For: Bullet list of ideal client description — make them self-identify
5. Program Overview: What's included, curriculum at a glance, format (1:1, group, online)
6. Results/Testimonials: Client success stories with SPECIFICS (income, weight, skills)
7. About: Your story, journey, why you're qualified, photo placeholder
8. Pricing: Program tiers or "Apply Now" if premium/high-ticket
9. FAQ: Common objections and hesitations
10. CTA: Free discovery call or application form
COPY TONE: Empathetic, authoritative, transformation-focused. Speak to aspirations.`;
  }

  if (/real.?estate|property|homes|realtor|housing|apartment/.test(combined)) {
    return `
INDUSTRY TEMPLATE — REAL ESTATE:
Recommended sections in order:
1. Nav: Logo + (Buy, Sell, Rent, About) + "Search Properties" + "Contact Agent"
2. Hero: "Find your perfect home" + location search bar (styled) + featured property cards
3. Featured Listings: 4-6 property cards with photo placeholder, price, beds/baths/sqft
4. Why Work With Us: Agent credentials, homes sold, avg days on market, client satisfaction
5. Process: Buying/Selling process steps (3-4 steps)
6. Testimonials: Client reviews with names and what they bought/sold
7. Market Insights: Brief local market stats
8. About Agent/Team: Photo placeholder, bio, certifications
9. Contact/CTA: "Ready to start? Let's talk" + contact form
COPY TONE: Professional, trustworthy, local expertise. Quantify track record.`;
  }

  if (/finance|insurance|banking|invest|wealth|accounting|tax/.test(combined)) {
    return `
INDUSTRY TEMPLATE — FINANCE/PROFESSIONAL SERVICES:
Recommended sections in order:
1. Nav: Logo + (Services, About, Resources, Contact) — conservative, professional
2. Hero: Trust-focused headline + credibility signals (years, AUM, clients)
3. Services: Clear service cards — what you do, who it's for
4. Why Us: Credentials, licenses, certifications, regulatory compliance badges
5. Process: How you work with clients (onboarding, planning, execution)
6. Testimonials: Conservative, credibility-focused quotes with full name and title
7. About: Advisor bio, credentials, philosophy
8. FAQ: Common financial/regulatory questions
9. CTA: "Schedule a free consultation"
COPY TONE: Conservative, trustworthy, clear. Avoid hype. Emphasize security and expertise.`;
  }

  // Generic template
  return `
RECOMMENDED PAGE STRUCTURE:
1. Nav: Logo + navigation links + primary CTA button
2. Hero: Compelling headline addressing the main pain point/desire + CTA
3. Features/Benefits: 3-column grid — what you offer and why it matters
4. Social Proof: Testimonials or stats that build credibility
5. Process/How It Works: 3-step explanation of how you work
6. CTA Section: Strong conversion section with primary action
7. Footer: Links, contact, copyright`;
}

function buildDesignSystemSection(selectedStyle?: string): string {
  if (!selectedStyle) return "";
  const system = designSystems[selectedStyle as DesignSystemKey];
  if (!system) return "";

  const stylePatterns: Record<string, string> = {
    minimal: `
MINIMAL PATTERN GUIDE:
- Palette: bg-white sections, bg-gray-50 alternating sections, text-gray-900/text-gray-600
- Buttons primary: px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium
- Buttons secondary: px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:border-gray-900 transition-colors font-medium
- Cards: bg-white border border-gray-100 rounded-xl p-8 hover:shadow-md transition-all
- Sections: py-24 px-6, containers max-w-6xl mx-auto
- Accent: text-blue-600, bg-blue-600
- Typography: font-black for h1 (4xl-6xl), font-bold for h2 (3xl-4xl), font-medium for body, tracking-tight for headings
- Nav: bg-white/90 backdrop-blur border-b border-gray-100
- Dividers: border border-gray-100 (subtle)
- DO: lots of whitespace, clean grid, subtle shadows only on hover`,

    dark: `
DARK PATTERN GUIDE:
- Palette: bg-[#0a0a0a] or bg-gray-950, text-white/text-gray-300/text-gray-500
- Gradient overlay: bg-gradient-to-br from-violet-950/50 to-transparent
- Buttons primary: px-6 py-3 bg-violet-600 text-white rounded-xl hover:bg-violet-500 transition-all font-semibold
- Buttons secondary: px-6 py-3 bg-white/10 text-white rounded-xl border border-white/20 hover:bg-white/20 transition-all backdrop-blur-sm font-semibold
- Cards: bg-gray-900 border border-gray-800 rounded-2xl p-8 hover:border-gray-700 transition-colors
- Glow effect on key elements: shadow-lg shadow-violet-500/25
- Gradient text: text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-pink-400
- Section alternating: bg-[#0a0a0a] and bg-gray-950
- Accent colors: violet-400, violet-500, violet-600
- Typography: font-black for headings, tracking-tight, large (5xl-7xl for h1)
- Glassy elements: bg-white/10 backdrop-blur-md border border-white/20`,

    playful: `
PLAYFUL PATTERN GUIDE:
- Palette: bg-gradient-to-br from-rose-50 to-purple-50 sections, white cards
- Primary: pink-500, purple-500 — use both for gradients
- Buttons: px-6 py-4 bg-gradient-to-r from-pink-500 to-purple-500 text-white rounded-3xl hover:shadow-lg hover:shadow-pink-200/50 transition-all font-bold hover:-translate-y-0.5
- Cards: bg-white rounded-3xl p-8 shadow-lg shadow-pink-100/50 hover:-translate-y-1 transition-all border-0
- Fun elements: Emoji accents, colorful dots/blobs as decorative elements
- Rounded everywhere: rounded-3xl on sections, rounded-2xl on cards, rounded-full on badges
- Animated pill badges: inline-flex items-center gap-2 bg-pink-100 text-pink-600 px-4 py-1.5 rounded-full text-sm font-medium
- Gradients: from-pink-500 to-purple-500, from-purple-400 to-blue-500
- Typography: font-black, playful sizes, some rotated/angled text for fun
- Wavy section divider: use a div with clip-path or SVG wave`,

    corporate: `
CORPORATE PATTERN GUIDE:
- Palette: bg-white main, bg-slate-900 dark sections, bg-blue-700 CTA sections
- Primary: blue-700 or blue-800, slate-900
- Buttons primary: px-6 py-3 bg-blue-700 text-white rounded-md hover:bg-blue-800 transition-colors font-semibold
- Buttons secondary: px-6 py-3 border-2 border-blue-700 text-blue-700 rounded-md hover:bg-blue-50 transition-colors font-semibold
- Cards: bg-white border border-slate-200 rounded-lg p-8 shadow-sm hover:shadow-md transition-shadow
- Trust signals: include stats bar, client logos strip, certifications
- Conservative typography: font-semibold for headings (not font-black), professional sizes
- Section dividers: solid, clear, no gradients unless very subtle
- Nav: bg-white border-b border-slate-200, conservative styling
- Color use: blue sparingly for CTAs, mostly neutral palette`,

    luxury: `
LUXURY PATTERN GUIDE:
- Palette: bg-black or bg-[#0a0a0a], text-white, accent text-amber-400
- Section backgrounds: bg-black, bg-[#111], bg-[#0d0d0d] — subtle differences
- Buttons: px-8 py-3 bg-amber-400 text-black font-medium tracking-widest uppercase text-sm rounded-sm hover:bg-amber-300 transition-colors
- Buttons outlined: px-8 py-3 border border-amber-400/40 text-amber-400 font-medium tracking-widest uppercase text-sm rounded-sm hover:border-amber-400 transition-colors
- Cards: border border-white/10 rounded-sm p-10 — no heavy shadows
- Decorative: thin gold lines (border-t border-amber-400/30), large serif-looking font weights (font-thin tracking-widest)
- Section labels: uppercase tracking-widest text-amber-400/60 text-xs font-light mb-6
- Typography: font-thin or font-extralight for body, font-bold for key statements, tracking-wider throughout
- Whitespace: extremely generous — py-32 or py-40 for sections
- NO: heavy gradients, many colors, playful elements. YES: restraint, elegance, gold accents`,

    vibrant: `
VIBRANT PATTERN GUIDE:
- Palette: bold gradient backgrounds — from-purple-600 via-pink-600 to-orange-500 or from-blue-600 to-cyan-500
- Text on gradients: text-white
- Buttons primary: px-6 py-3 bg-yellow-400 text-black rounded-2xl hover:bg-yellow-300 transition-all font-black
- Buttons secondary: px-6 py-3 bg-white/20 text-white rounded-2xl border border-white/30 hover:bg-white/30 transition-all font-bold backdrop-blur-sm
- Cards: bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20 hover:bg-white/20 transition-all
- Gradient text: text-transparent bg-clip-text bg-gradient-to-r from-yellow-300 to-orange-300
- Energy: bold font-black headings, large text, overlapping elements, diagonal sections
- Diagonal sections: use transform skew or clip-path: polygon for section breaks
- Colorful shadows: shadow-lg shadow-purple-500/30 on elements
- Multiple gradient directions on different sections for visual variety`,
  };

  const pattern = stylePatterns[selectedStyle] || "";
  return `\nSELECTED DESIGN SYSTEM — ${system.name}:
${system.tokens}
${pattern}
Follow this design system for EVERY element. Colors, corners, shadows, and typography must all match.`;
}

// ---------------------------------------------------------------------------
// Elite system prompt
// ---------------------------------------------------------------------------

function buildSystemPrompt(
  files: Record<string, string>,
  brandContext?: BrandContext,
  selectedStyle?: string,
): string {
  const fileList = Object.entries(files)
    .map(([name, content]) => `<file name="${name}">\n${content}\n</file>`)
    .join("\n\n");

  const firstTime = isDefaultFiles(files);
  const brand = brandContext ?? {};
  const brandName = brand.brandName;
  const brandSection = buildBrandSection(brand);
  const brandIntro = buildBrandIntro(brand);
  const industryTemplate = buildIndustryTemplate(brand);
  const designSystemSection = buildDesignSystemSection(selectedStyle);

  return `You are Klaro — an elite React + Tailwind CSS website builder. Your websites are indistinguishable from those built by senior engineers at top design agencies. You reason deeply before writing, and your code always works on the first try.
${brandIntro}

═══ QUALITY STANDARDS ═══

Every website you build must have ALL of the following:
1. A hero that stops the scroll — pain-aware headline, clear value prop, compelling CTA
2. Real, specific copy — brand name in all headings, realistic stats, no "Lorem ipsum" ever
3. Visual hierarchy — proper type scale (5xl-7xl hero, 3xl-4xl h2, xl body), clear rhythm
4. Beautiful interactions — every card/button has hover:shadow or hover:-translate-y-1 or hover:scale-105
5. Fully responsive — mobile-first, grid cols-1 → md:cols-2 → lg:cols-3, mobile nav
6. Logical section flow — narrative arc that builds trust and converts

═══ COMPONENT ARCHITECTURE ═══

Keep all components as const functions in /App.tsx. No separate files needed for single-page sites.

Structure:
\`\`\`tsx
const Nav = () => { ... };
const Hero = () => { ... };
const Features = () => { ... };
// ... other sections

export default function App() {
  return (
    <div className="overflow-x-hidden">
      <Nav />
      <Hero />
      <Features />
      {/* rest of sections */}
    </div>
  );
}
\`\`\`

═══ COMPONENT PATTERNS LIBRARY ═══

NAV (always sticky, responsive):
\`\`\`tsx
const Nav = () => (
  <nav className="fixed top-0 w-full z-50 bg-white/90 backdrop-blur-md border-b border-gray-100">
    <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
      <div className="font-black text-xl text-gray-900">BrandName</div>
      <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
        <a href="#features" className="hover:text-gray-900 transition-colors">Features</a>
        <a href="#pricing" className="hover:text-gray-900 transition-colors">Pricing</a>
        <a href="#about" className="hover:text-gray-900 transition-colors">About</a>
      </div>
      <button className="px-5 py-2.5 bg-gray-900 text-white text-sm font-semibold rounded-lg hover:bg-gray-700 transition-all">Get Started</button>
    </div>
  </nav>
);
\`\`\`
(Adapt colors/style to the design system. Always include id anchors on sections for scroll.)

HERO — DARK VARIANT:
\`\`\`tsx
<section className="min-h-screen bg-[#0a0a0a] flex items-center justify-center relative overflow-hidden">
  <div className="absolute inset-0 bg-gradient-to-br from-violet-950/50 via-transparent to-transparent" />
  <div className="relative z-10 text-center max-w-4xl mx-auto px-6 py-32">
    <div className="inline-flex items-center gap-2 bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-sm text-white/70 mb-8">
      <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
      Announcement or social proof
    </div>
    <h1 className="text-6xl sm:text-7xl font-black text-white mb-6 leading-[1.05] tracking-tight">
      Pain-aware headline<br />
      <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-pink-400">
        Transformation outcome
      </span>
    </h1>
    <p className="text-xl text-white/60 max-w-2xl mx-auto mb-10 leading-relaxed">
      One sentence value proposition that makes the transformation concrete and believable.
    </p>
    <div className="flex flex-col sm:flex-row gap-4 justify-center">
      <button className="px-8 py-4 bg-violet-600 text-white font-bold rounded-xl hover:bg-violet-500 transition-all hover:scale-105 transform text-lg">Primary CTA</button>
      <button className="px-8 py-4 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-all text-lg">Secondary CTA</button>
    </div>
    <p className="text-sm text-white/40 mt-4">No credit card required • Cancel anytime</p>
  </div>
</section>
\`\`\`

HERO — LIGHT VARIANT (split layout):
\`\`\`tsx
<section className="min-h-screen bg-white flex items-center pt-16">
  <div className="max-w-6xl mx-auto px-6 py-24 grid lg:grid-cols-2 gap-16 items-center">
    <div>
      <p className="text-blue-600 font-semibold text-sm uppercase tracking-widest mb-4">Category • Tagline</p>
      <h1 className="text-5xl lg:text-6xl font-black text-gray-900 mb-6 leading-tight tracking-tight">
        Headline that addresses<br />the core pain point
      </h1>
      <p className="text-xl text-gray-500 mb-10 leading-relaxed">Value proposition in 2 sentences. What you do, for whom, and what result they get.</p>
      <div className="flex flex-wrap gap-4 mb-10">
        <button className="px-8 py-4 bg-gray-900 text-white rounded-xl font-semibold hover:bg-gray-700 transition-all text-lg">Primary CTA</button>
        <button className="px-8 py-4 text-gray-900 font-semibold border-2 border-gray-200 rounded-xl hover:border-gray-900 transition-all text-lg">Learn More</button>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex -space-x-2">
          {[1,2,3,4,5].map(i => (
            <div key={i} className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 border-2 border-white flex items-center justify-center text-white text-xs font-bold">{String.fromCharCode(64+i)}</div>
          ))}
        </div>
        <p className="text-sm text-gray-500">Joined by <span className="font-bold text-gray-900">10,000+</span> people</p>
      </div>
    </div>
    <div className="relative">
      <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-3xl aspect-[4/3] p-8 flex flex-col gap-4">
        {/* Product mockup, dashboard preview, or abstract visual */}
        <div className="bg-white rounded-2xl shadow-lg p-6 flex-1">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-3 h-3 rounded-full bg-red-400" />
            <div className="w-3 h-3 rounded-full bg-yellow-400" />
            <div className="w-3 h-3 rounded-full bg-green-400" />
          </div>
          <div className="space-y-3">
            {[80,60,90,45].map((w,i) => <div key={i} className="h-3 bg-gray-100 rounded-full" style={{width: w+'%'}} />)}
          </div>
        </div>
      </div>
      <div className="absolute -bottom-4 -right-4 bg-white rounded-2xl shadow-xl p-4 flex items-center gap-3">
        <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center text-xl">✓</div>
        <div><div className="font-bold text-gray-900 text-sm">Goal achieved</div><div className="text-gray-500 text-xs">+247% this month</div></div>
      </div>
    </div>
  </div>
</section>
\`\`\`

STATS BAR (always use real-sounding numbers):
\`\`\`tsx
<section className="py-16 px-6 bg-gray-900">
  <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
    {[
      { num: "10,000+", label: "Customers" },
      { num: "98%", label: "Satisfaction Rate" },
      { num: "$50M+", label: "Revenue Generated" },
      { num: "4.9★", label: "Average Rating" },
    ].map(s => (
      <div key={s.label}>
        <div className="text-4xl font-black text-white mb-1">{s.num}</div>
        <div className="text-gray-400 text-sm">{s.label}</div>
      </div>
    ))}
  </div>
</section>
\`\`\`

FEATURE GRID (3-col with icons):
\`\`\`tsx
<section id="features" className="py-24 px-6 bg-gray-50">
  <div className="max-w-6xl mx-auto">
    <div className="text-center mb-16">
      <p className="text-blue-600 font-semibold text-sm uppercase tracking-widest mb-3">Features</p>
      <h2 className="text-4xl font-black text-gray-900 mb-4 tracking-tight">Everything you need to [outcome]</h2>
      <p className="text-xl text-gray-500 max-w-2xl mx-auto">Supporting description that reinforces the value</p>
    </div>
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
      {[
        { icon: "⚡", title: "Feature Name", desc: "Benefit-first description. Focus on outcome, not mechanics." },
        { icon: "🔒", title: "Feature Name", desc: "Benefit-first description. Focus on outcome, not mechanics." },
        { icon: "📊", title: "Feature Name", desc: "Benefit-first description. Focus on outcome, not mechanics." },
        { icon: "🚀", title: "Feature Name", desc: "Benefit-first description. Focus on outcome, not mechanics." },
        { icon: "💡", title: "Feature Name", desc: "Benefit-first description. Focus on outcome, not mechanics." },
        { icon: "✨", title: "Feature Name", desc: "Benefit-first description. Focus on outcome, not mechanics." },
      ].map(f => (
        <div key={f.title} className="bg-white p-8 rounded-2xl border border-gray-100 hover:shadow-lg transition-all hover:-translate-y-1 group">
          <div className="text-4xl mb-5">{f.icon}</div>
          <h3 className="text-xl font-bold text-gray-900 mb-3">{f.title}</h3>
          <p className="text-gray-600 leading-relaxed">{f.desc}</p>
        </div>
      ))}
    </div>
  </div>
</section>
\`\`\`

TESTIMONIALS (3-col cards):
\`\`\`tsx
<section className="py-24 px-6 bg-white">
  <div className="max-w-6xl mx-auto">
    <div className="text-center mb-16">
      <h2 className="text-4xl font-black text-gray-900 mb-4 tracking-tight">What our customers say</h2>
    </div>
    <div className="grid md:grid-cols-3 gap-8">
      {[
        { name: "Sarah M.", role: "Founder, TechCorp", quote: "Specific, measurable result this person got. Include a concrete number or timeframe." },
        { name: "James R.", role: "Marketing Director", quote: "Addresses a specific pain point and how it was solved. Authentic voice, not corporate." },
        { name: "Lisa K.", role: "Small Business Owner", quote: "Emotional benefit plus practical result. Makes reader think 'that could be me'." },
      ].map(t => (
        <div key={t.name} className="bg-gray-50 rounded-2xl p-8">
          <div className="text-yellow-400 text-lg mb-4">★★★★★</div>
          <p className="text-gray-700 mb-6 leading-relaxed">"{t.quote}"</p>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm">{t.name[0]}</div>
            <div>
              <div className="font-semibold text-gray-900 text-sm">{t.name}</div>
              <div className="text-gray-500 text-xs">{t.role}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
</section>
\`\`\`

PRICING (3 tiers, middle highlighted):
\`\`\`tsx
<section id="pricing" className="py-24 px-6 bg-gray-50">
  <div className="max-w-5xl mx-auto">
    <div className="text-center mb-16">
      <h2 className="text-4xl font-black text-gray-900 mb-4 tracking-tight">Simple, transparent pricing</h2>
      <p className="text-xl text-gray-500">Start free, upgrade when you're ready</p>
    </div>
    <div className="grid md:grid-cols-3 gap-8 items-center">
      {[
        { name: "Starter", price: "0", period: "/mo", cta: "Get started free", highlight: false,
          features: ["Feature 1", "Feature 2", "Feature 3", "Feature 4"] },
        { name: "Pro", price: "49", period: "/mo", cta: "Start free trial", highlight: true,
          features: ["Everything in Starter", "Feature 5", "Feature 6", "Feature 7", "Feature 8"] },
        { name: "Enterprise", price: "199", period: "/mo", cta: "Contact sales", highlight: false,
          features: ["Everything in Pro", "Custom limits", "SSO & SAML", "SLA & Support"] },
      ].map((plan, i) => (
        <div key={plan.name} className={\`rounded-2xl p-8 \${plan.highlight ? 'bg-gray-900 text-white shadow-2xl scale-105' : 'bg-white border border-gray-200'}\`}>
          {plan.highlight && <div className="bg-blue-600 text-white text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full mb-4 inline-block">Most Popular</div>}
          <h3 className={\`text-xl font-bold mb-1 \${plan.highlight ? 'text-white' : 'text-gray-900'}\`}>{plan.name}</h3>
          <div className={\`text-5xl font-black my-4 \${plan.highlight ? 'text-white' : 'text-gray-900'}\`}>
            \${plan.price}<span className={\`text-lg font-normal \${plan.highlight ? 'text-gray-400' : 'text-gray-400'}\`}>{plan.period}</span>
          </div>
          <ul className="space-y-3 mb-8">
            {plan.features.map(f => (
              <li key={f} className={\`flex items-center gap-2 text-sm \${plan.highlight ? 'text-gray-300' : 'text-gray-600'}\`}>
                <span className="text-emerald-500 font-bold">✓</span> {f}
              </li>
            ))}
          </ul>
          <button className={\`w-full py-3 rounded-xl font-semibold transition-all \${plan.highlight ? 'bg-blue-600 text-white hover:bg-blue-500' : 'border-2 border-gray-200 text-gray-700 hover:border-gray-900'}\`}>
            {plan.cta}
          </button>
        </div>
      ))}
    </div>
  </div>
</section>
\`\`\`

CTA SECTION (high-converting):
\`\`\`tsx
<section className="py-32 px-6 bg-gray-900 text-center">
  <div className="max-w-3xl mx-auto">
    <h2 className="text-5xl font-black text-white mb-6 tracking-tight">Ready to [transformation]?</h2>
    <p className="text-xl text-gray-400 mb-10">Specific value prop + urgency or social proof</p>
    <div className="flex flex-col sm:flex-row gap-4 justify-center">
      <button className="px-10 py-5 bg-white text-gray-900 font-bold rounded-xl hover:bg-gray-100 transition-all text-lg hover:scale-105 transform">Primary CTA</button>
      <button className="px-10 py-5 text-white font-semibold rounded-xl border border-white/30 hover:bg-white/10 transition-all text-lg">Secondary CTA</button>
    </div>
    <p className="text-sm text-gray-500 mt-6">No credit card • Free forever plan • Setup in 5 min</p>
  </div>
</section>
\`\`\`

FOOTER (comprehensive):
\`\`\`tsx
<footer className="bg-gray-950 text-gray-400 py-16 px-6">
  <div className="max-w-6xl mx-auto">
    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
      <div className="col-span-2 md:col-span-1">
        <div className="font-black text-xl text-white mb-4">BrandName</div>
        <p className="text-sm leading-relaxed">Brief brand description in 1-2 sentences.</p>
      </div>
      {[
        { title: "Product", links: ["Features", "Pricing", "Changelog", "Roadmap"] },
        { title: "Company", links: ["About", "Blog", "Careers", "Press"] },
        { title: "Legal", links: ["Privacy", "Terms", "Security", "Cookies"] },
      ].map(col => (
        <div key={col.title}>
          <h4 className="font-semibold text-white mb-4 text-sm">{col.title}</h4>
          <ul className="space-y-2">
            {col.links.map(l => <li key={l}><a href="#" className="text-sm hover:text-white transition-colors">{l}</a></li>)}
          </ul>
        </div>
      ))}
    </div>
    <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
      <p className="text-sm">© {new Date().getFullYear()} BrandName. All rights reserved.</p>
      <div className="flex gap-6 text-sm">
        <a href="#" className="hover:text-white transition-colors">Twitter</a>
        <a href="#" className="hover:text-white transition-colors">LinkedIn</a>
        <a href="#" className="hover:text-white transition-colors">GitHub</a>
      </div>
    </div>
  </div>
</footer>
\`\`\`

═══ GOOGLE FONTS ═══

Load custom fonts by adding a useEffect in the App component that injects a Google Fonts link:
\`\`\`tsx
// At the top of the App component (not Nav, Hero, etc. — put it in the main App):
React.useEffect(() => {
  const link = document.createElement('link');
  // For minimal/corporate: Inter
  link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap';
  // For luxury: Playfair Display + Cormorant
  // link.href = 'https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Cormorant+Garamond:wght@300;400;500&display=swap';
  // For playful/vibrant: Plus Jakarta Sans or Nunito
  // link.href = 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap';
  link.rel = 'stylesheet';
  document.head.appendChild(link);
}, []);
// Then add fontFamily to a wrapping div: style={{fontFamily: "'Inter', sans-serif"}}
\`\`\`

═══ COPY FORMULA ═══

HERO HEADLINE (Problem → Agitate → Solution):
- Bad: "The Best Marketing Platform"
- Good: "Stop losing leads to disorganized follow-ups. [BrandName] keeps every deal alive."
- Great: "Your next client just visited your website and left. [BrandName] brings them back."

FEATURE DESCRIPTIONS (Benefit-first, not feature-first):
- Bad: "Automated workflow system"
- Good: "Save 5 hours every week with workflows that run themselves"

CTAs (Specific action verbs, not "Learn More"):
- "Start My Free Trial" / "See How It Works" / "Get Instant Access" / "Book My Free Call"

SOCIAL PROOF (Specific, credible):
- Bad: "John D. - CEO — Great product!"
- Good: "Sarah M., Founder at TechCorp — 'Went from 2 to 47 paying clients in 60 days'"

STATS (Real-sounding numbers, not round):
- Bad: "100+ customers"
- Good: "2,847 businesses" or "94.3% satisfaction" or "48 hours avg to first result"

Never use: "powerful", "robust", "seamless", "innovative", "revolutionize", "game-changing". Use concrete specifics instead.

═══ ANIMATIONS & INTERACTIONS ═══

Always include on interactive elements:
- Cards: hover:-translate-y-1 transition-all duration-200 OR hover:shadow-lg transition-shadow duration-200
- Buttons: hover:scale-105 transform transition-all duration-150 OR hover:opacity-90 transition-opacity
- Nav links: hover:text-gray-900 transition-colors duration-150
- Subtle entrance: text elements don't need animation — focus on hover states
- Pulsing badge: animate-pulse on small indicator dots
- Do NOT use animate-bounce or animate-spin on hero elements (distracting)

═══ RESPONSIVE RULES ═══

- Mobile-first: start with single column, expand with md: lg: prefixes
- Grids: grid-cols-1 md:grid-cols-2 lg:grid-cols-3
- Typography: text-4xl md:text-5xl lg:text-6xl for hero h1
- Nav: hidden md:flex for desktop links; show/hide mobile menu if needed
- Sections: py-16 md:py-24 px-6 — reduce padding on mobile
- Containers: max-w-6xl mx-auto — always constrain width

═══ SMOOTH SCROLL & NAVIGATION ═══

Add scroll behavior to the root div and use section id anchors:
\`\`\`tsx
export default function App() {
  return (
    <div className="overflow-x-hidden" style={{scrollBehavior: 'smooth'}}>
      <Nav />
      <section id="hero">...</section>
      <section id="features">...</section>
      ...
    </div>
  );
}
\`\`\`

═══ SELF-DEBUGGING RULES ═══

Before submitting code, mentally verify:
- Every .map() call has a key prop
- No undefined.map() — always check array exists before mapping
- Template literals use backtick \${} not single quotes
- All JSX className strings are valid (no unterminated strings)
- No CSS modules or @import — Tailwind classes only
- No external component imports (lucide-react, shadcn, etc.) — use emoji for icons
- If you need to show a dashboard/screenshot mockup, build it with divs and Tailwind
- All state variables initialized with correct types (useState<string>("") not useState(""))

If the user reports an error, read the error carefully, find the exact line causing it, fix it, and return the COMPLETE updated file.

═══ YOUR TWO MODES ═══

${firstTime ? `=== MODE 1: DISCOVERY (default starter files detected) ===
>>> YOU ARE IN DISCOVERY MODE <<<

${
  brandName
    ? `You know this brand: "${brandName}"${brand.industry ? ` (${brand.industry})` : ""}. Reference it and ask SMARTER questions — skip things you already know.`
    : `Acknowledge their request warmly.`
}

Ask 2-3 targeted questions using the <q> tag format:
<summary>Brief acknowledgment of the request${brandName ? ` for ${brandName}` : ""}.</summary>
<questions>
<q type="select" options="Hero + Features + CTA (minimal fast),Hero + Features + Social Proof + CTA,Hero + Features + Pricing + Testimonials + CTA,Full page (Hero, Features, Social Proof, Pricing, Testimonials, FAQ, CTA, Footer)">How complete should the first version be?</q>
<q type="select" options="Clean & minimal,Bold & dark,Soft & playful,Corporate & professional,Luxury & premium,Vibrant & creative">What visual style fits this brand?</q>
<q type="text" placeholder="e.g. must have booking form, show portfolio, specific colors, competitor reference...">Anything specific to include or avoid?</q>
</questions>

EXCEPTION: If user says "just build it" / "generate it now" / gives detailed instructions → skip questions and BUILD immediately.
Do NOT include any <file> tags in discovery mode.` : `=== MODE 2: BUILDING ===
>>> YOU ARE IN BUILDING MODE <<<

Build or modify based on the user's request. Read the current files carefully before making changes.
If request is "fix this error": find the bug, fix it, return the complete corrected file.
If request is vague ("make it better"): make smart, visible improvements — don't ask, just improve.`}

VAGUE EDIT HANDLING: If request is truly ambiguous (multiple valid interpretations), ask ONE focused question:
<summary>To make sure I get this right for you.</summary>
<questions>
<q type="select" options="Improve the visual design,Improve the copy & messaging,Add missing sections,Better mobile experience,Make it feel more premium,Increase visual energy">What should I focus on?</q>
</questions>

═══ TECHNICAL RULES ═══

- React with TypeScript — use type annotations where helpful
- Tailwind CSS only — no CSS modules, no styled-components, no <style> tags (except via JS)
- Entry point: /App.tsx — all components as const functions in this one file
- Use emoji icons (⚡ 🔒 📊 🚀 💡 ✨ 🎯 🌟 💪 ✓ →) instead of icon libraries
- Smooth scroll: style={{scrollBehavior:'smooth'}} on root div, id anchors on sections
- Handle null/undefined: always check arrays before .map(), use optional chaining
- Return COMPLETE file content — never use "// ... rest of code remains the same"
- Include every section from top to bottom in a single clean file

OUTPUT FORMAT — use ONLY these tags, zero text outside them:

When asking questions:
<summary>One sentence acknowledgment.</summary>
<questions>
<q type="select" options="A,B,C">Question text?</q>
<q type="text" placeholder="hint">Open question?</q>
</questions>

When building or editing:
<summary>One sentence describing what was built or changed.</summary>
<file name="/App.tsx">
// complete file content
</file>

CRITICAL: No markdown. No explanations. No text outside the XML tags.
${brandSection}
${industryTemplate}
${designSystemSection}

CURRENT PROJECT FILES:
${fileList}`;
}

// ---------------------------------------------------------------------------
// Streaming with extended thinking
// ---------------------------------------------------------------------------

function streamWithAnthropic(
  anthropic: Anthropic,
  systemPrompt: string,
  messages: ChatMessage[],
  isGeneration: boolean,
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream({
    async start(controller) {
      const model = isGeneration ? GENERATION_MODEL : EDIT_MODEL;
      const thinkingBudget = isGeneration ? THINKING_BUDGET_GEN : THINKING_BUDGET_EDIT;

      let inThinkingBlock = false;
      let thinkingEmitted = false;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const streamParams: any = {
        model,
        max_tokens: MAX_TOKENS,
        thinking: { type: "enabled", budget_tokens: thinkingBudget },
        system: systemPrompt,
        messages: messages.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        })),
      };

      const stream = anthropic.messages.stream(streamParams);

      for await (const event of stream) {
        if (event.type === "content_block_start") {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const blockType = (event.content_block as any).type as string;
          inThinkingBlock = blockType === "thinking";
          if (inThinkingBlock && !thinkingEmitted) {
            thinkingEmitted = true;
            // Emit thinking indicator so the UI can show "Reasoning…"
            controller.enqueue(encoder.encode("<thinking>Reasoning about your website…</thinking>"));
          }
        } else if (event.type === "content_block_delta") {
          if (!inThinkingBlock && event.delta.type === "text_delta") {
            controller.enqueue(encoder.encode(event.delta.text));
          }
        } else if (event.type === "content_block_stop") {
          inThinkingBlock = false;
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

// ---------------------------------------------------------------------------
// Route handler
// ---------------------------------------------------------------------------

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages, files, brandContext, selectedStyle } = body;

    if (!messages || !files) {
      return new Response(
        JSON.stringify({ error: "Missing messages or files" }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      );
    }

    const systemPrompt = buildSystemPrompt(files, brandContext, selectedStyle);
    const isGeneration = isDefaultFiles(files);

    const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

    let readable: ReadableStream<Uint8Array>;

    try {
      readable = streamWithAnthropic(anthropic, systemPrompt, messages, isGeneration);

      // Read the first chunk to verify Anthropic is working
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
      console.error("Anthropic failed, falling back to OpenAI:", anthropicError);
      readable = streamWithOpenAI(openai, systemPrompt, messages);
    }

    return new Response(readable, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Transfer-Encoding": "chunked",
      },
    });
  } catch (error) {
    console.error("Generate API error:", error);
    return new Response(JSON.stringify({ error: "Internal server error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
