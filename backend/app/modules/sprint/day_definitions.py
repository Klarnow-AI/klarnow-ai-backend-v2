"""Day definitions with Build/Improve mode variations."""

from typing import TypedDict


class DayContent(TypedDict):
    """Content for a day in a specific mode."""
    tasks: list[str]
    playbook: str
    scripts: list[dict]  # list of {title, script}


class DayDefinition(TypedDict):
    """Definition for a sprint day."""
    day_number: int
    title: str
    win_condition: str
    requires_mode_variation: bool
    build_mode: DayContent | None
    improve_mode: DayContent | None


DAY_DEFINITIONS: list[DayDefinition] = [
    {
        "day_number": 0,
        "title": "Foundation",
        "win_condition": "USP locked and CTA confirmed",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Lock brand name",
                "Define your USP (Unique Selling Proposition)",
                "Set your primary call-to-action"
            ],
            "playbook": "Today is about establishing the foundation of your business identity. Lock in your brand name, clarify what makes you unique, and decide on the primary action you want customers to take.",
            "scripts": []
        },
        "improve_mode": None  # Same as build
    },
    {
        "day_number": 1,
        "title": "Offer",
        "win_condition": "Offer updated or locked",
        "requires_mode_variation": True,
        "build_mode": {
            "tasks": [
                "Define what you're selling",
                "Set price range",
                "Clarify deliverables"
            ],
            "playbook": "Create a clear, compelling offer. What exactly are you selling? What's included? What's the price range? Make it concrete enough that someone can say yes or no immediately.",
            "scripts": [
                {
                    "title": "Offer Pitch Template",
                    "script": "We help [target audience] achieve [outcome] through [what you do]. Starting from [price]."
                }
            ]
        },
        "improve_mode": {
            "tasks": [
                "Review current offer",
                "Identify weak points",
                "Tighten messaging"
            ],
            "playbook": "Audit your existing offer. Is it clear? Is the value obvious? Are there barriers? Tighten the copy, adjust the price if needed, and remove confusion.",
            "scripts": [
                {
                    "title": "Offer Audit Checklist",
                    "script": "1. Can someone understand it in 5 seconds? 2. Is the price clear? 3. Are the deliverables specific? 4. Does it address their pain?"
                }
            ]
        }
    },
    {
        "day_number": 2,
        "title": "USP + Audience",
        "win_condition": "USP visible in messaging",
        "requires_mode_variation": True,
        "build_mode": {
            "tasks": [
                "Define target audience",
                "Identify primary pain point",
                "Craft USP statement"
            ],
            "playbook": "Who are you serving? What problem do you solve for them? What makes your solution different from everyone else's? Answer these three questions with brutal clarity.",
            "scripts": [
                {
                    "title": "USP Formula",
                    "script": "We help [specific audience] solve [specific problem] with [unique approach] so they can [desired outcome]."
                }
            ]
        },
        "improve_mode": {
            "tasks": [
                "Extract USP from reviews/testimonials",
                "Identify patterns in customer feedback",
                "Refine positioning"
            ],
            "playbook": "Your customers already know your USP—go find it. Read your reviews, look at testimonials, check DMs. What do people say about you that they don't say about competitors? Extract and amplify that.",
            "scripts": [
                {
                    "title": "Review Mining Template",
                    "script": "Search for: 'unlike', 'different', 'only', 'better than'. These words signal your USP in customer language."
                }
            ]
        }
    },
    {
        "day_number": 3,
        "title": "Confidence Script",
        "win_condition": "3 voice notes sent",
        "requires_mode_variation": True,
        "build_mode": {
            "tasks": [
                "Write pitch script",
                "Practice delivery",
                "Send 3 voice notes to potential customers"
            ],
            "playbook": "You need to be able to pitch your offer confidently in under 60 seconds. Write your script, practice it out loud, then record 3 voice notes to real people. If you can't explain it clearly, you can't sell it.",
            "scripts": [
                {
                    "title": "60-Second Pitch Structure",
                    "script": "Hi [Name], I help [who] with [problem]. Most people struggle with [pain point], but we [solution]. Interested in [CTA]?"
                }
            ]
        },
        "improve_mode": {
            "tasks": [
                "List common objections",
                "Craft responses to each",
                "Test new objection handling"
            ],
            "playbook": "You've heard the objections before: 'too expensive', 'not now', 'need to think about it'. Write down the 5 most common objections you get, then craft clear, confident responses. Test them in your next 3 conversations.",
            "scripts": [
                {
                    "title": "Objection Response Framework",
                    "script": "Acknowledge → Reframe → Evidence → Ask: 'I hear you. What most people find is [reframe]. For example, [evidence]. Does that make sense?'"
                }
            ]
        }
    },
    {
        "day_number": 4,
        "title": "Ad Factory",
        "win_condition": "Assets generated and first ad shipped",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Generate video scripts",
                "Create shot list",
                "Export first ad",
                "Ship content"
            ],
            "playbook": "Today you create your first marketing assets. Use AI to generate video scripts, define your shots, and export your first ad. Post it so your sprint keeps moving.",
            "scripts": [
                {
                    "title": "Hook Formula",
                    "script": "Start with the outcome: 'How to [achieve result] without [common pain]' or 'The [X] method that [benefit]'"
                }
            ]
        },
        "improve_mode": None  # Same as build
    },
    {
        "day_number": 5,
        "title": "Posters",
        "win_condition": "Poster posted + broadcast sent",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Generate poster variants",
                "Export best option",
                "Post on social media",
                "Send broadcast message"
            ],
            "playbook": "Create visual assets that communicate your offer at a glance. Generate poster variants, pick the best one, export it, and post it. Then send a broadcast to your audience.",
            "scripts": [
                {
                    "title": "Broadcast Template",
                    "script": "Just dropped something new: [brief value prop]. Check it out → [link]. Questions? Reply to this."
                }
            ]
        },
        "improve_mode": None  # Same as build
    },
    {
        "day_number": 6,
        "title": "Conversion Destination",
        "win_condition": "Conversion destination ready",
        "requires_mode_variation": True,
        "build_mode": {
            "tasks": [
                "Create page draft",
                "Add proof",
                "Review copy",
                "Confirm CTA"
            ],
            "playbook": "Build the page where people will convert. This could be a landing page, booking page, or product page. Make sure the CTA and contact flow are clear. Add proof if you have it.",
            "scripts": []
        },
        "improve_mode": {
            "tasks": [
                "Review existing destination",
                "Optimize copy",
                "Add proof",
                "Reduce friction"
            ],
            "playbook": "You already have a conversion destination—make it better. Update copy to match your refined USP, add proof, and remove friction points.",
            "scripts": []
        }
    },
    {
        "day_number": 7,
        "title": "Publish / Confirm",
        "win_condition": "Link shared with 10 people",
        "requires_mode_variation": True,
        "build_mode": {
            "tasks": [
                "Publish page",
                "Test conversion flow",
                "Share link with 10 people"
            ],
            "playbook": "Make it live. Publish your website, test the full flow (from click to submission), then share the link with 10 real people. Get it in front of humans today.",
            "scripts": [
                {
                    "title": "Share Script",
                    "script": "Hey [Name], just launched [offer]. Would love your feedback → [link]. Takes 2 minutes to check out."
                }
            ]
        },
        "improve_mode": {
            "tasks": [
                "Confirm destination URL",
                "Add proof if missing",
                "Share link with 10 people"
            ],
            "playbook": "Confirm your conversion destination is ready. Make sure proof is visible. Then share it with 10 people—colleagues, past customers, or warm leads. Get traffic flowing.",
            "scripts": [
                {
                    "title": "Reactivation Script",
                    "script": "Hey [Name], updated [offer page]. Cleaned it up and made it clearer. Check it out → [link]. Let me know what you think."
                }
            ]
        }
    },
    {
        "day_number": 8,
        "title": "Response Rules",
        "win_condition": "Response rules saved and test enquiry handled",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Generate response templates",
                "Customize templates",
                "Lock response rules",
                "Test with mock enquiry"
            ],
            "playbook": "Lock in your response system. Generate templates for common scenarios (enquiries, objections, booking requests), customize them to your voice, then lock them. From today onward, you have copy-paste responses ready.",
            "scripts": [
                {
                    "title": "Initial Enquiry Template",
                    "script": "Hey [Name]! Thanks for reaching out. [Quick value statement]. Are you looking to [CTA]? If so, [next step]."
                }
            ]
        },
        "improve_mode": None  # Same as build
    },
    {
        "day_number": 9,
        "title": "Follow-up",
        "win_condition": "Leads moved from New → Contacted",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Review follow-up queue",
                "Contact all pending leads",
                "Mark tasks complete"
            ],
            "playbook": "Clear your follow-up queue. Every lead that came in needs a response. Copy the template, send the message, mark it done. No lead sits in 'New' for more than 24 hours.",
            "scripts": [
                {
                    "title": "Follow-up Template (Touch 2)",
                    "script": "Hey [Name], following up on [previous message]. Still interested in [offer]? Happy to answer any questions."
                }
            ]
        },
        "improve_mode": None  # Same as build
    },
    {
        "day_number": 10,
        "title": "Fix the Leak",
        "win_condition": "Improvement applied",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Identify one leak in the process",
                "Fix it live",
                "Document the change"
            ],
            "playbook": "Find one thing that's losing you customers and fix it today. Common leaks: unclear CTA, slow response time, confusing offer. Pick one, fix it, move on.",
            "scripts": []
        },
        "improve_mode": None  # Same as build
    },
    {
        "day_number": 11,
        "title": "Close Path",
        "win_condition": "Proposal ready or bundle created",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Create proposal template (service/coach) OR bundle offer (product)",
                "Set pricing",
                "Test send to one lead"
            ],
            "playbook": "Build your closing mechanism. If you're service/coach: create a proposal. If you're product: create a bundle or upsell offer. Make it ready to send today.",
            "scripts": [
                {
                    "title": "Proposal Intro",
                    "script": "Hey [Name], based on our conversation, here's what I'm proposing: [deliverables]. Timeline: [time]. Investment: [price]. Let me know if this works."
                }
            ]
        },
        "improve_mode": None  # Same as build
    },
    {
        "day_number": 12,
        "title": "Close Conversations",
        "win_condition": "3 closes attempted and next step requested",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Identify 3 qualified leads",
                "Send proposal/offer",
                "Request next step (call, payment, agreement)"
            ],
            "playbook": "Ask for the sale. Pick 3 qualified leads and send them your proposal or offer. Then ask: 'Does this work for you?' or 'Are you ready to move forward?' Don't be passive—close the loop.",
            "scripts": [
                {
                    "title": "Close Request",
                    "script": "Does this work for you? If yes, [next step: book call, make payment, sign agreement]. If not, what questions do you have?"
                }
            ]
        },
        "improve_mode": None  # Same as build
    },
    {
        "day_number": 13,
        "title": "Invoice / Payment",
        "win_condition": "Invoice or payment request sent",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Create invoice or payment link",
                "Send to accepted proposals",
                "Set payment follow-up reminder"
            ],
            "playbook": "Send the invoice. If they said yes, send the payment request immediately. Don't wait. Set a follow-up reminder for 24 hours if they don't pay.",
            "scripts": [
                {
                    "title": "Invoice Message",
                    "script": "Hey [Name], excited to get started! Here's the invoice: [link]. Once payment is received, we'll [next step]."
                }
            ]
        },
        "improve_mode": None  # Same as build
    },
    {
        "day_number": 14,
        "title": "Check-in",
        "win_condition": "Check-in complete and Sprint 2 created",
        "requires_mode_variation": False,
        "build_mode": {
            "tasks": [
                "Review sprint metrics",
                "Document wins and lessons",
                "Start Sprint 2"
            ],
            "playbook": "Review the sprint. Did you send a proposal? Did you send an invoice? What worked? What didn't? Document it, then reload for Sprint 2. The system continues.",
            "scripts": []
        },
        "improve_mode": None  # Same as build
    }
]


def get_day_definition(day_number: int) -> DayDefinition:
    """Get day definition by number."""
    for day in DAY_DEFINITIONS:
        if day["day_number"] == day_number:
            return day
    raise ValueError(f"Day {day_number} not found")


def get_day_content(day_number: int, mode: str) -> DayContent:
    """Get day content for specific mode (build or improve)."""
    day_def = get_day_definition(day_number)
    
    if not day_def["requires_mode_variation"]:
        # Same for both modes
        return day_def["build_mode"]
    
    if mode == "improve" and day_def["improve_mode"]:
        return day_def["improve_mode"]
    
    return day_def["build_mode"]


USP_CATEGORY_OPTIONS = [
    "Faster",
    "More reliable",
    "Better quality",
    "More specialised",
    "Better experience",
    "Better value",
    "Other",
]

DAY_CONVERSATION_STEPS: dict[int, list[dict]] = {
    0: [
        {"key": "has_existing_brand", "label": "Is this an existing brand?", "input_type": "choice"},
        {"key": "brand_url", "label": "Enter your website URL", "if_has_brand": True, "input_type": "input", "placeholder": "e.g. https://example.com"},
        {"key": "brand_name", "label": "What's your brand name?", "input_type": "input", "placeholder": "e.g. Acme Co"},
        {"key": "primary_cta", "label": "What's your primary call-to-action?", "input_type": "input", "placeholder": "e.g. Book a call"},
        {"key": "usp_category", "label": "Which USP category fits you best?", "input_type": "choice", "options": USP_CATEGORY_OPTIONS},
        {"key": "usp_statement", "label": "Why choose you over the obvious alternatives?", "input_type": "input", "placeholder": "e.g. We deliver in half the time"},
        {"key": "usp_proof", "label": "What proof point makes that true? (optional)", "input_type": "input", "placeholder": "e.g. 200+ projects delivered on time"},
        {"key": "proof_text", "label": "Any additional proof or testimonials? (optional)", "input_type": "textarea", "placeholder": "Additional proof or testimonials"},
    ],
    1: [
        {"key": "offer_one_liner", "label": "What's your offer in one sentence?", "input_type": "input", "placeholder": "e.g. We help busy founders launch in 30 days"},
    ],
    2: [
        {"key": "primary_pain", "label": "What's the primary pain point?", "input_type": "input", "placeholder": "e.g. Lack of time to focus on growth"},
        {"key": "primary_outcome", "label": "What's the primary outcome?", "input_type": "input", "placeholder": "e.g. 2x revenue in 90 days"},
    ],
    3: [
        {"key": "pitch_script", "label": "Write your pitch script (under 60 seconds)", "input_type": "textarea", "placeholder": "Hi [Name], I help [who] with [problem]..."},
        {"key": "voice_notes_sent", "label": "Have you sent 3 voice notes?", "input_type": "choice", "options": ["Yes", "Not yet"]},
    ],
}


def get_day_conversation_steps(day_number: int) -> list[dict]:
    """Get conversation step labels and keys for Day 0–3."""
    return DAY_CONVERSATION_STEPS.get(day_number, [])


def get_step_by_field_key(day_number: int, field_key: str) -> dict | None:
    """Get step config for a field_key within a day. Returns None if not found."""
    steps = DAY_CONVERSATION_STEPS.get(day_number, [])
    for s in steps:
        if s.get("key") == field_key:
            return s
    return None
