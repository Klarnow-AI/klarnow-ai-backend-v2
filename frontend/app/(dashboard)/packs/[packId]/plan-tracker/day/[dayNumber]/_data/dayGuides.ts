export interface DayGuide {
  dayNumber: number;
  title: string;
  overview: string;
  tasks: string[];
  tips: string[];
  expectedOutcome: string;
}

export const dayGuides: Record<number, DayGuide> = {
  0: {
    dayNumber: 0,
    title: "Foundation",
    overview: "Lock brand name, USP, and CTA. This is your foundation - everything else builds on what you define today.",
    tasks: [
      "Lock your brand name",
      "Define your USP (Unique Selling Proposition)",
      "Set your primary call-to-action",
      "Complete the Day 0 checklist"
    ],
    tips: [
      "Be specific - your USP should be unique to you",
      "Your CTA should be one clear action (e.g. Book a call)",
      "Don't overthink it - you can refine as you go"
    ],
    expectedOutcome: "USP locked and CTA confirmed. You're ready for Day 1."
  },
  1: {
    dayNumber: 1,
    title: "Offer",
    overview: "Build: create offer and price range. Improve: audit and tighten your existing offer.",
    tasks: [
      "Define what you're selling",
      "Set price range",
      "Clarify deliverables",
      "Confirm your offer is clear and believable"
    ],
    tips: [
      "One clear offer beats multiple confusing options",
      "Price according to value",
      "Make it concrete enough that someone can say yes or no immediately"
    ],
    expectedOutcome: "Offer updated or locked. You have clarity on what you're selling and at what price."
  },
  2: {
    dayNumber: 2,
    title: "USP + Audience",
    overview: "Build: create USP and audience. Improve: extract USP from reviews or site.",
    tasks: [
      "Define target audience",
      "Identify primary pain point",
      "Craft USP statement",
      "Complete pain/outcome selection"
    ],
    tips: [
      "Your customers already know your USP - check reviews and testimonials",
      "Pain should be urgent and specific",
      "Use their words, not marketing jargon"
    ],
    expectedOutcome: "USP visible in messaging. You know who you're serving and what makes you different."
  },
  3: {
    dayNumber: 3,
    title: "Confidence script",
    overview: "Build: create your pitch script and send 3 voice notes. Improve: fix objections with clear responses.",
    tasks: [
      "Write your pitch script (under 60 seconds)",
      "Practice delivery out loud",
      "Send 3 voice notes to potential customers",
      "List common objections and craft responses (improve mode)"
    ],
    tips: [
      "Structure: Hi [Name], I help [who] with [problem]. Most people struggle with [pain], but we [solution]. Interested in [CTA]?",
      "If you can't explain it clearly, you can't sell it",
      "Acknowledge → Reframe → Evidence → Ask"
    ],
    expectedOutcome: "Pitch script ready and 3 voice notes sent. Objections handled with confidence."
  },
  4: {
    dayNumber: 4,
    title: "Ad Factory",
    overview: "Generate video scripts and shot list. Ship content and log outreach.",
    tasks: [
      "Generate video scripts",
      "Create shot list",
      "Export first ad",
      "Ship content and log outreach"
    ],
    tips: [
      "Hook formula: start with the outcome - 'How to [result] without [pain]'",
      "Keep messaging consistent with Day 2 pain/outcome"
    ],
    expectedOutcome: "Scripts and shot list generated. First ad shipped and outreach logged."
  },
  5: {
    dayNumber: 5,
    title: "Posters",
    overview: "Generate poster variants. Post and send a broadcast.",
    tasks: [
      "Generate poster variants",
      "Export best option",
      "Post on social media",
      "Send broadcast message",
      "Log outreach"
    ],
    tips: [
      "Posters should communicate your offer at a glance",
      "One clear CTA per poster"
    ],
    expectedOutcome: "Poster posted and broadcast sent. Outreach logged."
  },
  6: {
    dayNumber: 6,
    title: "Conversion destination",
    overview: "Build: create page draft. Improve: optimise existing destination.",
    tasks: [
      "Create page draft (or optimise existing)",
      "Add lead filter",
      "Add proof",
      "Review copy"
    ],
    tips: [
      "Lead filter qualifies traffic (price, location, who it's for)",
      "Add proof if you have it",
      "Remove friction points"
    ],
    expectedOutcome: "Conversion destination ready. Build: page draft done. Improve: destination optimised."
  },
  7: {
    dayNumber: 7,
    title: "Publish / Confirm",
    overview: "Build: publish page and share link with 10 people. Improve: confirm destination and add proof.",
    tasks: [
      "Publish page (or confirm destination URL)",
      "Test conversion flow",
      "Add proof if missing",
      "Share link with 10 people"
    ],
    tips: [
      "Test the full flow from click to submission",
      "Get it in front of real people today"
    ],
    expectedOutcome: "Link shared with 10 people. Destination confirmed and proof added."
  },
  8: {
    dayNumber: 8,
    title: "Response rules",
    overview: "Lock response rules and start your outreach habit. Generate templates, customise, then lock.",
    tasks: [
      "Generate response templates",
      "Customise to your voice",
      "Lock response rules",
      "Test with a mock enquiry"
    ],
    tips: [
      "Templates for: enquiries, objections, booking requests",
      "From today you have copy-paste responses ready"
    ],
    expectedOutcome: "Response rules locked. Outreach habit started."
  },
  9: {
    dayNumber: 9,
    title: "Follow-up",
    overview: "Clear your follow-up queue. Every lead gets a response.",
    tasks: [
      "Review follow-up queue",
      "Contact all pending leads",
      "Mark tasks complete"
    ],
    tips: [
      "No lead sits in 'New' for more than 24 hours",
      "Copy template, send message, mark done"
    ],
    expectedOutcome: "Follow-up queue cleared. Leads moved from New to Contacted."
  },
  10: {
    dayNumber: 10,
    title: "Fix the leak",
    overview: "Apply one improvement live. Find one thing losing you customers and fix it today.",
    tasks: [
      "Identify one leak (unclear CTA, slow response, confusing offer)",
      "Fix it live",
      "Document the change"
    ],
    tips: [
      "Pick one thing only",
      "Common leaks: unclear CTA, slow response time, confusing offer"
    ],
    expectedOutcome: "One improvement applied live."
  },
  11: {
    dayNumber: 11,
    title: "Close path",
    overview: "Service/coach: create proposal. Product: create bundle offer.",
    tasks: [
      "Create proposal template (service/coach) OR bundle offer (product)",
      "Set pricing",
      "Test send to one lead"
    ],
    tips: [
      "Make it ready to send today",
      "Clear deliverables and next step"
    ],
    expectedOutcome: "Proposal ready or bundle created. Close path ready."
  },
  12: {
    dayNumber: 12,
    title: "Close conversations",
    overview: "Ask for the sale. Send proposal/offer to qualified leads and request next step.",
    tasks: [
      "Identify 3 qualified leads",
      "Send proposal or offer",
      "Request next step (call, payment, agreement)"
    ],
    tips: [
      "Don't be passive - close the loop",
      "Ask: 'Does this work for you?' or 'Ready to move forward?'"
    ],
    expectedOutcome: "3 closes attempted. Next step requested."
  },
  13: {
    dayNumber: 13,
    title: "Invoice / Payment",
    overview: "Send invoice or payment request. Get paid.",
    tasks: [
      "Create invoice or payment link",
      "Send to accepted proposals",
      "Set payment follow-up reminder"
    ],
    tips: [
      "Send the invoice immediately when they say yes",
      "Follow up in 24 hours if they don't pay"
    ],
    expectedOutcome: "Invoice or payment request sent."
  },
  14: {
    dayNumber: 14,
    title: "Check-in",
    overview: "Review sprint metrics, document wins and lessons, start Sprint 2.",
    tasks: [
      "Review sprint metrics",
      "Document wins and lessons",
      "Complete check-in to start Sprint 2"
    ],
    tips: [
      "Be honest about what didn't work",
      "Momentum compounds - keep going"
    ],
    expectedOutcome: "Check-in complete. Sprint 2 created."
  }
};

export function getDayGuide(dayNumber: number): DayGuide | null {
  return dayGuides[dayNumber] || null;
}
