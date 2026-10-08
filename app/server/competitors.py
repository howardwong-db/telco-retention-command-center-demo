"""Structured competitor intelligence facts + talk tracks for the demo."""

COMPETITOR_FACTS = [
    {
        "name": "T-Mobile Home Internet",
        "market_share": 38,
        "positioning": "Aggressive $50 flat pricing, no contracts, bundled with T-Mobile mobile.",
        "pricing": "$50/mo flat ($35/mo with eligible T-Mobile mobile plan). No annual contract.",
        "weaknesses": [
            "Fixed-wireless speeds swing 33-245 Mbps and degrade under network congestion",
            "Performance drops in bad weather and during peak evening hours",
            "No live TV product - cord-cutters must add a separate streaming stack",
            "No wired reliability guarantee; latency spikes hurt gaming and video calls",
        ],
        "best_counter": "TelcoABC One Bundle $49.99",
        "counter_offer_id": "OFF-01",
        "talk_track": (
            "Acknowledge the price, then pivot to reliability: \"T-Mobile advertises $50, but "
            "that's fixed-wireless - your speed can drop from 245 down to 33 Mbps when the tower "
            "gets busy or the weather turns. Our TelcoABC One Bundle is $49.99 for wired internet "
            "that doesn't flinch during the evening rush, plus a free mobile line and no data caps. "
            "You get the same price with a connection you can actually count on for work and streaming.\""
        ),
    },
    {
        "name": "AT&T Fiber",
        "market_share": 24,
        "positioning": "Symmetrical fiber speeds, strong brand, promo-driven acquisition pricing.",
        "pricing": "$55/mo intro; jumps +$25-35/mo after the 12-month promo. No mobile bundle included by default.",
        "weaknesses": [
            "Promo pricing expires and bills jump $25-35/mo in month 13",
            "No mobile line bundled - customers pay full price for wireless elsewhere",
            "Fiber footprint is limited; many addresses can't actually get it",
            "Install windows and equipment fees add friction",
        ],
        "best_counter": "12-Month Price Lock",
        "counter_offer_id": "OFF-03",
        "talk_track": (
            "Lead with the bill shock: \"AT&T's intro rate looks great until month 13 when it "
            "climbs $25 to $35 a month. Let me lock your TelcoABC rate for 12 full months so there "
            "are no surprises - and unlike AT&T, I can add a free mobile line so your total household "
            "bill actually goes down, not up.\""
        ),
    },
    {
        "name": "Verizon 5G Home",
        "market_share": 12,
        "positioning": "5G fixed wireless, deep discounts only when paired with Verizon mobile.",
        "pricing": "$60/mo standalone ($35/mo only with a qualifying Verizon mobile plan - $90-115 combined household spend).",
        "weaknesses": [
            "The headline $35 price requires an expensive Verizon mobile plan - $90-115 combined",
            "5G fixed wireless shares the same congestion and signal-variability issues",
            "Standalone price is $60/mo - higher than TelcoABC's bundle",
            "No TV offering; indoor signal depends on tower proximity",
        ],
        "best_counter": "TelcoABC One Bundle $49.99",
        "counter_offer_id": "OFF-01",
        "talk_track": (
            "Expose the bundle math: \"That $35 Verizon price only exists if you're paying $90 to "
            "$115 a month for their mobile plan - so the 'deal' is locked behind an expensive "
            "wireless bill. TelcoABC One is $49.99 for reliable wired internet AND includes a mobile "
            "line, so you get the bundle savings without being trapped into premium wireless pricing.\""
        ),
    },
    {
        "name": "Frontier Fiber",
        "market_share": 11,
        "positioning": "Value fiber in select metros, symmetrical speeds, price-led.",
        "pricing": "$45-70/mo depending on tier; availability limited to fiber-built neighborhoods.",
        "weaknesses": [
            "Sparse fiber footprint - most addresses fall back to slow DSL",
            "Customer-service and reliability reputation lags",
            "No integrated mobile bundle",
            "Speed tiers vary widely by neighborhood build quality",
        ],
        "best_counter": "Free Upgrade to Ultra",
        "counter_offer_id": "OFF-04",
        "talk_track": (
            "Match the speed story: \"If speed is what's pulling you toward Frontier, I can upgrade "
            "you to TelcoABC Ultra for free - faster speeds on a network that's already built and "
            "proven in your neighborhood, plus the mobile bundle Frontier can't offer.\""
        ),
    },
    {
        "name": "Google Fiber",
        "market_share": 8,
        "positioning": "Premium symmetrical gig/multi-gig fiber, simple pricing, tech-forward brand.",
        "pricing": "$70-100/mo for 1-2 Gig tiers; available in a handful of metros only.",
        "weaknesses": [
            "Extremely limited availability - only a few cities",
            "Premium pricing at the top tiers ($100/mo for 2 Gig)",
            "No mobile bundle and no live-TV product",
            "Multi-gig speeds exceed what most households actually use",
        ],
        "best_counter": "TelcoABC One Bundle $49.99",
        "counter_offer_id": "OFF-01",
        "talk_track": (
            "Right-size the need: \"Google Fiber's multi-gig is impressive, but most homes never "
            "use a fraction of it - and you're paying premium prices for headroom you won't touch. "
            "TelcoABC One gives you all the speed a household actually needs at $49.99 with a mobile "
            "line included, and it's available at your address today.\""
        ),
    },
    {
        "name": "Verizon Fios",
        "market_share": 7,
        "positioning": "Established fiber in the Northeast, strong reliability, higher price point.",
        "pricing": "$65-90/mo; best pricing gated behind Verizon mobile enrollment.",
        "weaknesses": [
            "Higher standalone pricing than TelcoABC's bundle",
            "Best rates require a Verizon mobile plan (bundle lock-in)",
            "Geographically limited to legacy Fios build areas",
            "Perk value (gift cards, streaming) is short-lived promo bait",
        ],
        "best_counter": "TelcoABC One Bundle $49.99",
        "counter_offer_id": "OFF-01",
        "talk_track": (
            "Break the bundle lock-in: \"Fios is a solid network, but their best pricing chains you "
            "to a Verizon mobile plan. TelcoABC One is $49.99, includes a mobile line, and doesn't "
            "make you rebuild your entire wireless setup to get the savings.\""
        ),
    },
]
