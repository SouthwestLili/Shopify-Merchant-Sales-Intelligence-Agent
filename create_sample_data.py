"""
create_sample_data.py

Reads shopify_merchants.csv (real filtered merchants) and generates
realistic sample output files for dashboard testing — no API credits needed.

Generates:
  merchant_analysis.json
  merchant_emails.json
  merchant_enrichment.json

Usage:
    python create_sample_data.py
    python dashboard.py          # then open http://localhost:5000
"""

import json
import pandas as pd
from pathlib import Path

DIR = Path(__file__).resolve().parent
CSV_PATH = DIR / "shopify_merchants.csv"

# ── Per-merchant sample data keyed by domain ──────────────────────────────────
# Each entry contains enrichment, analysis, and email copy tailored to the
# real merchant's title/positioning from shopify_merchants.csv.

MERCHANT_DETAILS: dict[str, dict] = {

    "mccc-sportswear.com": {
        "description": "Fashionable sportswear for every season. Trendy activewear and casual clothing for men and women.",
        "products": ["Hoodies", "Joggers", "T-Shirts", "Sports Bras", "Jackets"],
        "tools_detected": ["Google Analytics", "Meta Pixel"],
        "price_range": "$25 – $95",
        "blog_topics": ["Style Tips", "Season Lookbook", "New Arrivals"],
        "social_proof": {"review_count": 320, "has_testimonials": False},
        "score": 7,
        "score_reasoning": "Low-tech fashion brand with no email marketing or loyalty program — clear stack gap with a fashion-active audience.",
        "snapshot": "Mccc Sportswear is a fashion-forward activewear brand selling seasonal clothing across men's and women's categories. With minimal marketing tech (Google Analytics + Meta Pixel only), they are leaving email revenue and repeat purchases uncaptured.",
        "pain_points": [
            "No email marketing tool — zero automated customer communication",
            "No loyalty program for a repeat-purchase product category",
            "No review app — existing reviews not being displayed or amplified",
            "No abandoned cart recovery — lost revenue every day",
        ],
        "hooks": [
            "Sportswear is a repeat-purchase category — customers need new pieces every season",
            "With Meta Pixel active you're running paid ads, but without email you can't retain what you acquire",
            "320 reviews sitting invisible is a conversion problem on every product page",
        ],
        "channel": "email",
        "timing": "Pre-season launch (Jan for spring, Aug for fall) when new drops go live",
        "value_prop": "Build the email + loyalty engine that turns one-time buyers into seasonal regulars",
        "email_a_subject": "Mccc's Meta spend vs. zero email",
        "email_a_body": "Mccc Sportswear is running Meta ads to bring in customers — but without email marketing, every customer relationship ends the moment they close the tab.\n\nWe help fashion brands like yours set up Klaviyo + a loyalty program in one afternoon: cart recovery, welcome flows, and a points system for repeat seasonal buyers.\n\nWould fixing cart abandonment first make sense as a starting point?",
        "email_b_subject": "How ActivePulse grew repeat revenue 3x without more ad spend",
        "email_b_body": "ActivePulse (sportswear brand, similar AOV to Mccc) added email automation + a seasonal loyalty program last spring. In 90 days:\n• Repeat purchase rate: +3x\n• Email-attributed revenue: 28% of total\n• Ad spend: unchanged\n\nAll from customers they already had. Happy to share the exact setup.",
        "email_c_subject": "What does Mccc's repeat purchase rate look like right now?",
        "email_c_body": "Quick question — do you know what percentage of Mccc customers come back for a second seasonal purchase?\n\nFor sportswear brands without email automation, it's typically under 15%. With Klaviyo flows and a loyalty program, it's usually 35–50%.\n\nI can model what that gap is worth for Mccc in revenue terms — takes five minutes. Want me to run it?",
    },

    "shoplsdcouture.com": {
        "description": "Bold fashion and custom gowns. Couture apparel and statement accessories for the fashion-forward woman.",
        "products": ["Custom Gowns", "Evening Wear", "Bold Separates", "Accessories", "Bridal"],
        "tools_detected": ["Google Analytics", "Meta Pixel", "Klaviyo"],
        "price_range": "$120 – $850",
        "blog_topics": ["Style Inspiration", "Custom Orders", "Event Looks"],
        "social_proof": {"review_count": 640, "has_testimonials": True},
        "score": 8,
        "score_reasoning": "High-AOV couture brand with Klaviyo but no loyalty or review app — custom gown customers are perfect for a VIP loyalty tier.",
        "snapshot": "LSD Couture is a bold fashion house offering custom gowns and statement pieces at a high AOV ($120–$850). They run Klaviyo but have no loyalty program or dedicated review platform — a significant gap for a brand whose clients often make multiple occasion purchases.",
        "pain_points": [
            "No loyalty program despite high AOV and repeat occasion-wear purchases",
            "No review app — 640 reviews not being surfaced on product pages",
            "No referral mechanic — satisfied couture clients are the best word-of-mouth channel",
            "No post-purchase sequence for custom gown follow-up or upsell",
        ],
        "hooks": [
            "Custom gown clients often return for the next event — a VIP loyalty tier would lock in that repeat",
            "640 reviews with no display widget means visitors don't see your social proof before bouncing",
            "A referral program for couture clients can replace paid acquisition entirely",
        ],
        "channel": "email",
        "timing": "Pre-event season (March for spring galas, October for holiday events)",
        "value_prop": "Turn your couture clientele into a VIP loyalty community — referrals, rewards, and review display in one app",
        "email_a_subject": "LSD Couture's repeat gown clients — are you capturing them?",
        "email_a_body": "LSD Couture has something most fashion brands don't — customers who come back for every major occasion. Without a loyalty program, those repeat clients have no reason to choose you over a competitor next time.\n\nWe help high-AOV fashion brands build a VIP tier connected to Klaviyo: custom reward points, birthday perks, and a referral mechanic that turns your best clients into sales reps.\n\nWant to see what a VIP tier looks like for a couture brand? 15 minutes.",
        "email_b_subject": "How Maison Elara retained 70% of custom clients year-over-year",
        "email_b_body": "Maison Elara (custom gown brand, similar AOV to LSD Couture) added our VIP loyalty + review display in one day. In 12 months:\n• Repeat client rate: 70% (up from 31%)\n• Referral-driven new clients: 22% of new revenue\n• Review display added 9% to PDP conversion\n\nTheir clients feel recognized now — not just transacted with.",
        "email_c_subject": "What happens to a LSD Couture client after their gown is delivered?",
        "email_c_body": "Genuine question — after a custom gown is delivered, what's the next touchpoint a LSD Couture client receives?\n\nFor most couture brands without a loyalty program, the answer is: nothing, until they need another gown. By then they may have forgotten you.\n\nI can show you what a minimal VIP follow-up sequence looks like for a brand your size. 15 minutes — worth it?",
    },

    "theaestheticsloft.com": {
        "description": "Radiant skin and beauty experts in Milford, CT. Professional skincare treatments and at-home product line.",
        "products": ["Facials", "Chemical Peels", "Skincare Products", "Gift Cards", "Memberships"],
        "tools_detected": ["Google Analytics"],
        "price_range": "$65 – $380",
        "blog_topics": ["Skin Tips", "Treatment Guide", "Seasonal Skin Care"],
        "social_proof": {"review_count": 215, "has_testimonials": True},
        "score": 7,
        "score_reasoning": "Local beauty clinic with Shopify store and minimal tech — email and loyalty would transform one-time clients into recurring members.",
        "snapshot": "The Aesthetics Loft is a professional skincare clinic in Milford, CT selling both in-clinic treatments and at-home products via Shopify. With only Google Analytics installed, they have no email marketing, no loyalty, and no automated follow-up — leaving significant recurring revenue on the table.",
        "pain_points": [
            "No email marketing — clinic clients receive zero automated post-treatment follow-up",
            "No loyalty program for a high-frequency, recurring-service business model",
            "No review display app — 215 reviews not shown on product/service pages",
            "No membership or subscription mechanic despite being an ideal use case",
        ],
        "hooks": [
            "Clinic clients are the highest-loyalty customer type — a membership program is the obvious next step",
            "Post-treatment email sequences (product recommendations, rebooking reminders) are leaving revenue uncaptured",
            "215 reviews with no display widget means new visitors don't see your social proof",
        ],
        "channel": "email",
        "timing": "New Year (skin resolution season) and pre-summer (SPF + brightening treatments)",
        "value_prop": "Turn clinic visits into a recurring membership model — loyalty + automated rebooking flows in one app",
        "email_a_subject": "The Aesthetics Loft clients — are they coming back?",
        "email_a_body": "The Aesthetics Loft has a strong client base and a clear result-driven service. The gap: without email flows, clients have no automated reason to rebook or repurchase at-home products between visits.\n\nWe help beauty clinics set up Klaviyo + a membership-style loyalty program: post-treatment sequences, product repurchase reminders, and a points system that rewards booking frequency.\n\nWould a rebooking flow be the right first step for your practice?",
        "email_b_subject": "How Glow Studio built a $12k/mo membership base",
        "email_b_body": "Glow Studio (CT beauty clinic, similar service mix to The Aesthetics Loft) launched a membership loyalty program and automated email sequence in one afternoon. In 6 months:\n• Membership subscribers: 180 clients @ $65/mo\n• Rebooking rate: up from 38% to 71%\n• At-home product revenue: +$4,200/mo\n\nAll from clients they already had. Happy to share their setup.",
        "email_c_subject": "What's The Aesthetics Loft rebooking rate right now?",
        "email_c_body": "Quick benchmark — what percentage of The Aesthetics Loft clients rebook within 8 weeks of their last treatment?\n\nFor beauty clinics without automated rebooking emails and a loyalty program, it's typically 35–45%. With them, it's 65–78%.\n\nI can model what that gap is worth in monthly recurring revenue for your practice. Interested in the numbers?",
    },

    "theskinbarmedispa.com": {
        "description": "Enhance Your Natural Beauty at TheSkinBar Knoxville. Medical spa offering advanced skin treatments and premium skincare.",
        "products": ["Botox", "Fillers", "Laser Treatments", "Medical-Grade Skincare", "Memberships"],
        "tools_detected": ["Google Analytics", "Meta Pixel", "Klaviyo", "Gorgias"],
        "price_range": "$150 – $1,200",
        "blog_topics": ["Treatment Education", "Before & After", "Skin Health"],
        "social_proof": {"review_count": 1840, "has_testimonials": True},
        "score": 9,
        "score_reasoning": "High-spend medispa ($114k tech spend) with Klaviyo and Gorgias but no loyalty program — extremely high LTV clients with zero retention mechanic.",
        "snapshot": "TheSkinBar Knoxville is a high-end medical spa with a $114k/mo technology investment, nearly 2,000 reviews, active Klaviyo, and Gorgias for client support. Despite a sophisticated stack they have no loyalty or membership program — a critical gap for a business where client LTV can exceed $5,000.",
        "pain_points": [
            "No loyalty program for a high-LTV medical spa client base — missing recurring membership revenue",
            "No referral mechanic despite medispa clients being natural word-of-mouth advocates",
            "Gorgias cost rising without a self-serve loyalty portal to answer common questions",
            "No VIP tier to retain top-spending clients",
        ],
        "hooks": [
            "With $114k in monthly tech spend you're clearly investing in growth — loyalty is the missing retention layer",
            "Medispa clients with $1,200 treatments are the highest-LTV customers in beauty — a VIP tier would lock them in",
            "Nearly 2,000 reviews means you have a loyal client base that isn't being formally rewarded",
        ],
        "channel": "email",
        "timing": "January (new year aesthetic resolutions) and September (pre-holiday treatment rush)",
        "value_prop": "Build the VIP membership layer your high-LTV medispa clients deserve — loyalty + referrals connected to Klaviyo",
        "email_a_subject": "TheSkinBar's $1,200 clients — where's the VIP program?",
        "email_a_body": "TheSkinBar has built one of Knoxville's most sophisticated medispa stacks — Klaviyo, Gorgias, Meta Pixel, nearly 2,000 reviews. The gap that stands out: no loyalty or membership program for clients spending $150–$1,200 per visit.\n\nFor a practice at your level, a VIP tier isn't optional — it's the difference between clients who compare prices and clients who never leave.\n\nWe integrate directly with Klaviyo and Gorgias. Want to see what a TheSkinBar membership program could look like?",
        "email_b_subject": "How Illuminate MedSpa built $45k/mo in membership revenue",
        "email_b_body": "Illuminate MedSpa (TN, similar service mix to TheSkinBar) launched a VIP membership + referral program connected to Klaviyo. In 8 months:\n• Monthly membership revenue: $45,200\n• Referral-driven new clients: 34% of all new bookings\n• Gorgias ticket volume: -29% (members self-serve via loyalty portal)\n\nOne afternoon of setup. Happy to walk you through their exact tier structure.",
        "email_c_subject": "What percentage of TheSkinBar clients return for a second treatment?",
        "email_c_body": "Quick benchmark — for a medispa at TheSkinBar's level, what's your 6-month client return rate?\n\nFor high-end medspas without a formal loyalty program, it's typically 42–55%. With a VIP membership tier, it's 72–85%.\n\nOn $1,200 treatments, that gap is enormous in revenue terms. I can model it for TheSkinBar specifically — want me to run the numbers?",
    },

    "obroi.com": {
        "description": "Fashion online for women, men, kids and lifestyle. Trendy collections across all categories.",
        "products": ["Women's Clothing", "Men's Clothing", "Kids Fashion", "Accessories", "Lifestyle"],
        "tools_detected": ["Google Analytics", "Meta Pixel"],
        "price_range": "$18 – $120",
        "blog_topics": ["Style Trends", "Family Fashion", "Seasonal Picks"],
        "social_proof": {"review_count": 580, "has_testimonials": False},
        "score": 7,
        "score_reasoning": "Multi-category fashion retailer with broad audience and no email or loyalty tools — high volume potential with the right retention stack.",
        "snapshot": "Obroi is a multi-category fashion retailer serving women, men, and kids with trend-led collections at accessible price points ($18–$120). With only Google Analytics and Meta Pixel, they have no email automation, no loyalty program, and no review display — leaving repeat purchase revenue uncaptured across all customer segments.",
        "pain_points": [
            "No email marketing — no cart recovery, welcome flows, or post-purchase sequences",
            "No loyalty program despite a multi-category audience with high purchase frequency potential",
            "No review display app — social proof not visible on product pages",
            "Broad audience (women, men, kids) not being segmented for targeted email campaigns",
        ],
        "hooks": [
            "Multi-category fashion shoppers buy across segments — a family points program could 2x basket size",
            "Without email, every Meta ad acquisition is a one-time transaction",
            "580 reviews sitting unshown is a conversion problem across your entire catalog",
        ],
        "channel": "email",
        "timing": "Back-to-school (July–Aug) and holiday (Oct–Nov) — when multi-category fashion peaks",
        "value_prop": "Segment your family audience and automate retention — Klaviyo flows + loyalty for women, men, and kids in one app",
        "email_a_subject": "Obroi's family audience is un-segmented",
        "email_a_body": "Obroi serves women, men, and kids — one of the broadest fashion audiences on Shopify. The problem: without email segmentation, every customer gets the same message (or no message at all).\n\nWe help multi-category fashion brands set up Klaviyo with family-based segmentation: separate flows for women's, men's, and kids' buyers, plus a unified loyalty program where family points accumulate across all purchases.\n\nWould back-to-school season be the right time to launch this?",
        "email_b_subject": "How FamilyThreads 2x'd AOV with family loyalty points",
        "email_b_body": "FamilyThreads (multi-category fashion, similar structure to Obroi) launched a unified family loyalty program — points earned on kids, women's, and men's purchases all stack.\n\nIn 90 days:\n• Average order value: +2.1x (families shop across more categories per visit)\n• Repeat purchase rate: +88%\n• Email open rates: 41% (segmented vs. 12% generic)\n\nHappy to share their segmentation structure.",
        "email_c_subject": "What's Obroi's repeat purchase rate across customer segments?",
        "email_c_body": "Quick question — do you know whether your women's buyers, men's buyers, and kids' buyers have different repeat purchase rates?\n\nFor multi-category fashion brands without email segmentation, all three groups typically underperform because they get generic messaging. Segmented brands see 2–3x higher engagement per category.\n\nI can show you what a segmented setup looks like for Obroi. 15 minutes?",
    },

    "bthr.store": {
        "description": "Shop for all things clean beauty and skincare products online. Curated selection of non-toxic, wellness-focused beauty brands.",
        "products": ["Clean Skincare", "Non-Toxic Makeup", "Wellness Products", "Body Care", "Gift Sets"],
        "tools_detected": ["Google Analytics", "Meta Pixel", "Mailchimp"],
        "price_range": "$24 – $110",
        "blog_topics": ["Clean Beauty Guide", "Ingredient Spotlight", "Wellness Tips"],
        "social_proof": {"review_count": 730, "has_testimonials": True},
        "score": 8,
        "score_reasoning": "Clean beauty retailer using Mailchimp instead of Klaviyo — missing Shopify-native flows; strong candidate for stack upgrade with loyalty add-on.",
        "snapshot": "Beyond the Hot Room is an online clean beauty and skincare retailer with a curated wellness focus. They use Mailchimp for email (not Klaviyo) and have no loyalty program or review display app — standard gaps for a growing clean beauty brand at this stage.",
        "pain_points": [
            "Using Mailchimp — missing Shopify-native cart recovery, browse abandonment, and post-purchase flows",
            "No loyalty program for a category where brand values (clean, non-toxic) drive strong repeat loyalty",
            "No review display app — 730 reviews not visible on product pages",
            "No segmentation by product type (skincare vs. makeup vs. wellness) for targeted campaigns",
        ],
        "hooks": [
            "Clean beauty customers are among the most loyal in retail — your Mailchimp list is underserved",
            "Switching from Mailchimp to Shopify-native email unlocks cart recovery for every abandoned checkout",
            "730 reviews is significant social proof — it just needs to be displayed where shoppers can see it",
        ],
        "channel": "email",
        "timing": "New Year wellness reset (Jan) and Earth Day (April) — peak clean beauty intent moments",
        "value_prop": "Upgrade from Mailchimp to Klaviyo + loyalty — we migrate your list, build the flows, and add review display in one day",
        "email_a_subject": "Beyond the Hot Room's Mailchimp gap",
        "email_a_body": "Beyond the Hot Room has built a strong clean beauty audience — 730 reviews, a wellness-focused catalog, active social. The gap: Mailchimp can't trigger on Shopify events, so every abandoned cart, browse session, and post-purchase moment is silent.\n\nWe help clean beauty retailers make the switch to Klaviyo + loyalty in a single afternoon — list migration included, no data loss.\n\nIs fixing cart abandonment on your roadmap for Q1?",
        "email_b_subject": "How PureRoot 4x'd email revenue switching from Mailchimp",
        "email_b_body": "PureRoot (clean beauty retailer, similar AOV and values to Beyond the Hot Room) switched from Mailchimp to our Klaviyo + loyalty stack in one day.\n\nIn 90 days:\n• Email-attributed revenue: 4.2x\n• Cart recovery: $8,400 recovered in first 60 days\n• Repeat purchase rate: +61%\n\nSubscriber list moved over completely. Happy to share their migration process.",
        "email_c_subject": "How many Beyond the Hot Room carts go unrecovered each week?",
        "email_c_body": "Honest question — with Mailchimp, do you know how many Beyond the Hot Room checkouts are started but abandoned without a follow-up email?\n\nFor Shopify stores on Mailchimp, the answer is typically all of them — Mailchimp can't trigger on Shopify cart events without expensive workarounds.\n\nI can show you what that lost revenue looks like in dollar terms for your store. No pitch — just numbers. Interested?",
    },

    "yendrabeauty.com": {
        "description": "Preventative skincare for athletes and sensitive skin. Performance-focused formulas that work as hard as you do.",
        "products": ["SPF Moisturiser", "Post-Workout Cleanser", "Barrier Repair Serum", "Eye Cream", "Body Lotion"],
        "tools_detected": ["Google Analytics", "Meta Pixel", "Klaviyo"],
        "price_range": "$32 – $88",
        "blog_topics": ["Athlete Skincare Tips", "SPF Guide", "Post-Workout Routine", "Sensitive Skin"],
        "social_proof": {"review_count": 1120, "has_testimonials": True},
        "score": 9,
        "score_reasoning": "Niche beauty brand with strong Klaviyo usage, 1,100 reviews, and a loyal athlete community — no loyalty or review app despite a perfect subscription/repeat use case.",
        "snapshot": "Yendra Beauty is a niche skincare brand targeting athletes and sensitive skin types — a highly engaged, repeat-purchase audience. With 1,100+ reviews and active Klaviyo, they have strong foundations but are missing a loyalty program and review display app, leaving significant retention revenue uncaptured.",
        "pain_points": [
            "No loyalty program for a daily-use, repurchase-driven product line (SPF, cleanser, serum)",
            "No review display app — 1,100+ reviews not prominently shown on product pages",
            "No referral mechanic despite a passionate athlete community that influences each other's purchases",
            "No subscription mechanic for daily-use products — Klaviyo flows not paired with subscribe-and-save",
        ],
        "hooks": [
            "Athletes are the most routine-driven consumers — a points program with workout-themed rewards would resonate deeply",
            "1,100 reviews from a niche audience is exceptional social proof — it needs a display widget to convert",
            "Your athlete community sells for you — a referral program would capture that word-of-mouth",
        ],
        "channel": "email",
        "timing": "New Year training season (Jan) and pre-summer (May) — when athletes increase workout frequency",
        "value_prop": "Activate your athlete community — loyalty points, referrals, and review display all connected to Klaviyo",
        "email_a_subject": "Yendra's athlete community isn't being rewarded",
        "email_a_body": "Yendra Beauty has built something rare — 1,100+ reviews from a niche athlete and sensitive skin audience. Without a loyalty program, that community has no formal reason to stay, refer, or subscribe.\n\nWe help niche beauty brands activate their community: athlete-themed points, referral mechanics for gym/running communities, and a review display that shows your social proof on every product page.\n\nWant to see what a Yendra loyalty program could look like? 15 minutes.",
        "email_b_subject": "How TrailSkin 3x'd repeat purchases from their running community",
        "email_b_body": "TrailSkin (niche athlete skincare, similar community to Yendra) launched a 'miles = points' loyalty program — customers earned points for purchases and referrals from their training network.\n\nIn 6 months:\n• Repeat purchase rate: 3.1x\n• Referral-driven revenue: 28% of new sales\n• Community referral rate: 1 in 3 customers referred a training partner\n\nThe niche audience made it work extremely fast. Happy to share the structure.",
        "email_c_subject": "What does Yendra's repurchase rate look like for SPF and cleanser?",
        "email_c_body": "Quick question — for daily-use products like SPF and post-workout cleanser, what percentage of Yendra customers repurchase within 60 days?\n\nFor beauty brands without a loyalty or subscription mechanic, it's typically 22–30%. With one, athlete-targeted brands typically see 55–70%.\n\nI can model what that gap is worth for Yendra's specific SKU mix. Want me to run it?",
    },

    "franklysouthernboutique.com": {
        "description": "Women's fashion with a Southern heart. Boutique clothing, accessories, and gifts for the modern Southern woman.",
        "products": ["Dresses", "Tops", "Denim", "Accessories", "Gift Items"],
        "tools_detected": ["Google Analytics"],
        "price_range": "$28 – $115",
        "blog_topics": ["Style Inspiration", "Southern Living", "Gift Guides"],
        "social_proof": {"review_count": 290, "has_testimonials": True},
        "score": 7,
        "score_reasoning": "Small women's boutique with minimal tech stack and low tech spend — email + loyalty is the foundational upgrade this stage of boutique typically needs.",
        "snapshot": "Frankly Southern Boutique is a women's fashion boutique with a strong Southern identity and community feel. With only Google Analytics installed, they have no email marketing, no loyalty program, and no review display — the exact profile of a boutique ready for its first retention stack.",
        "pain_points": [
            "No email marketing at all — no cart recovery, welcome sequences, or seasonal campaigns",
            "No loyalty program despite a community-oriented boutique audience that values recognition",
            "No review display — existing testimonials not being leveraged on product pages",
            "No gift card promotion mechanic despite 'gift items' being a product category",
        ],
        "hooks": [
            "Southern boutique customers are deeply loyal to brands that feel personal — a loyalty program is on-brand",
            "Without email, every seasonal collection launch misses the customers who would most want to know",
            "Gift items as a category is an underused loyalty trigger — double points on gift purchases drives holiday revenue",
        ],
        "channel": "email",
        "timing": "Southern social season (spring) and holiday gifting (Nov–Dec)",
        "value_prop": "Build the boutique loyalty community your Southern customers already want — email + points in one afternoon",
        "email_a_subject": "Frankly Southern's community isn't getting emails",
        "email_a_body": "Frankly Southern Boutique has the brand personality that makes loyalty programs work — community-driven, values-led, personal. The gap: without email marketing, customers who love your boutique have no touchpoint between purchases.\n\nWe help Southern boutiques set up Klaviyo + a community loyalty program in one afternoon: seasonal campaigns, gift-double-points, and a welcome series that introduces new customers to your brand story.\n\nWould a seasonal campaign calendar be the right starting point?",
        "email_b_subject": "How Magnolia & Main 4x'd holiday revenue with email",
        "email_b_body": "Magnolia & Main (Southern women's boutique, similar positioning to Frankly Southern) launched email automation + a holiday loyalty program last October.\n\nIn 90 days:\n• Holiday email revenue: 4x vs. prior year\n• New loyalty members: 890\n• Gift card sales: +220%\n\nThe brand voice translated perfectly into email — it felt personal, not automated. Happy to share their campaign structure.",
        "email_c_subject": "What happens to a Frankly Southern customer between seasonal drops?",
        "email_c_body": "Honest question — what does the experience look like for a Frankly Southern customer between your seasonal collections?\n\nFor boutiques without email marketing, the answer is usually silence. No updates, no early access, no loyalty recognition — until they see a Meta ad or remember to visit the site.\n\nI can show you what a simple seasonal email calendar looks like for a boutique your size. 15 minutes — worth it?",
    },

    "troyabeauty.com": {
        "description": "Shop premium hair and beauty brands. Curated selection of professional-grade hair care, skincare, and beauty products.",
        "products": ["Professional Hair Care", "Premium Skincare", "Beauty Tools", "Hair Color", "Treatment Kits"],
        "tools_detected": ["Google Analytics", "Meta Pixel", "Klaviyo", "Searchanise"],
        "price_range": "$22 – $165",
        "blog_topics": ["Hair Care Guides", "Product Reviews", "Salon Secrets", "Beauty Trends"],
        "social_proof": {"review_count": 2140, "has_testimonials": True},
        "score": 8,
        "score_reasoning": "Premium multi-brand beauty retailer with Klaviyo and 2,100 reviews but no loyalty or review app — strong candidate with high purchase frequency.",
        "snapshot": "Troya Beauty is a premium multi-brand beauty retailer with 2,100+ reviews, active Klaviyo, and Searchanise for product discovery. Despite a strong commercial setup they have no loyalty program or review display app — a clear gap for a store where customers repurchase professional hair and skincare products regularly.",
        "pain_points": [
            "No loyalty program despite high repurchase frequency for professional hair and skincare products",
            "No review display app — 2,100 reviews not shown on product pages",
            "No referral mechanic — beauty enthusiasts with premium product knowledge are natural referrers",
            "No subscription mechanic for regularly repurchased products (shampoo, conditioner, treatment kits)",
        ],
        "hooks": [
            "Professional hair care is one of the highest-repurchase beauty categories — loyalty is the obvious move",
            "2,100 reviews is exceptional for a multi-brand retailer — they need to be visible on every product page",
            "Beauty enthusiasts who discover a premium retailer tell their friends — a referral program would capture that",
        ],
        "channel": "email",
        "timing": "New Year hair refresh (Jan) and pre-summer (April–May) — peak hair treatment seasons",
        "value_prop": "Turn your 2,100 reviews into conversion drivers and add loyalty for your repeat hair care buyers",
        "email_a_subject": "Troya's 2,100 reviews aren't showing up on product pages",
        "email_a_body": "Troya Beauty has built serious social proof — 2,100 reviews for a premium multi-brand beauty store is exceptional. The problem: without a review display app, most visitors never see them before making a purchase decision.\n\nWe add review display to every product page and connect a loyalty program for your repeat hair and skincare buyers — both pulling from your existing Klaviyo setup.\n\nWant to see what this looks like for Troya's catalog? 15 minutes.",
        "email_b_subject": "How LuxeHair Collective 3x'd repeat orders with loyalty",
        "email_b_body": "LuxeHair Collective (premium hair and beauty retailer, similar catalog to Troya) added review display + a loyalty program in one afternoon.\n\nIn 60 days:\n• On-site conversion: +14% (reviews visible on PDPs)\n• Repeat order rate: 3.1x\n• Subscription opt-in for top 10 SKUs: 22%\n\nSame customers — just properly retained. Happy to share their setup.",
        "email_c_subject": "What's Troya's repurchase rate for professional hair care SKUs?",
        "email_c_body": "Quick benchmark — for professional shampoos, conditioners, and treatment kits, what percentage of Troya customers reorder within 90 days?\n\nFor premium beauty retailers without a loyalty or subscription mechanic, it's typically 28–38%. With one, it jumps to 55–70%.\n\nI can model what that gap is worth for Troya's top-selling SKUs. Want me to run it?",
    },

    "mavenry.com": {
        "description": "MAVENRY — Fashion concept store offering curated contemporary fashion from independent designers.",
        "products": ["Designer Tops", "Statement Pieces", "Contemporary Dresses", "Accessories", "Limited Editions"],
        "tools_detected": ["Google Analytics", "Meta Pixel"],
        "price_range": "$45 – $280",
        "blog_topics": ["Designer Spotlight", "Style Guides", "New Season Arrivals"],
        "social_proof": {"review_count": 185, "has_testimonials": False},
        "score": 7,
        "score_reasoning": "Fashion concept store with curated designer positioning and minimal tech stack — loyalty would strengthen the editorial-brand relationship with their audience.",
        "snapshot": "Mavenry is an Egyptian fashion concept store with a curated, editorial approach to contemporary fashion from independent designers. With only Google Analytics and Meta Pixel installed, they have no email marketing, no loyalty program, and no review app — significant gaps for a brand whose positioning depends on customer relationships.",
        "pain_points": [
            "No email marketing — curated fashion drops and designer spotlights are not being communicated to past buyers",
            "No loyalty program despite a fashion-forward audience that values editorial exclusivity",
            "No review app — 185 reviews not amplified or displayed",
            "No early access or VIP mechanic for limited edition and designer drops",
        ],
        "hooks": [
            "Concept store audiences expect curation and early access — a VIP loyalty tier is on-brand",
            "Designer spotlight content translates perfectly into email campaigns that drive traffic to new arrivals",
            "Without email, every limited edition drop is invisible to past buyers until they see a paid ad",
        ],
        "channel": "email",
        "timing": "New season launches (Feb for spring, Sep for fall) — when concept stores have highest new-arrival intent",
        "value_prop": "Build the editorial VIP program your concept store audience expects — early access, curation drops, and designer loyalty in one app",
        "email_a_subject": "Mavenry's designer drops — are past buyers seeing them?",
        "email_a_body": "Mavenry has the editorial positioning that concept store audiences love — curated, independent designers, limited editions. The gap: without email marketing, past buyers find out about new drops only through paid ads or chance.\n\nWe help fashion concept stores build a VIP early-access program: new arrival emails, designer spotlight campaigns, and a loyalty tier for your most engaged buyers.\n\nWould early access emails for limited drops be the right first step?",
        "email_b_subject": "How Atelier24 built a 60% repeat rate for concept store buyers",
        "email_b_body": "Atelier24 (fashion concept store, similar editorial positioning to Mavenry) launched a VIP email program + designer loyalty tier. In one season:\n• Past buyer repeat rate: 60% (up from 19%)\n• New arrival email open rate: 44%\n• Limited drop sell-through: 94% within 48 hours\n\nThe VIP early-access mechanic made the difference — buyers felt chosen, not just marketed to.",
        "email_c_subject": "What percentage of Mavenry buyers come back for the next season?",
        "email_c_body": "Quick question — do you know what percentage of Mavenry customers purchase again within 6 months?\n\nFor fashion concept stores without email marketing and a loyalty program, first-season buyers typically don't return at all — they forget by the time the next collection arrives.\n\nI can show you what a minimal early-access email + VIP setup looks like for a concept store your size. 15 minutes?",
    },

    "wingweftgloves.com": {
        "description": "Fashionable customized gloves. Unique, bespoke gloves designed for style and self-expression.",
        "products": ["Custom Gloves", "Fashion Gloves", "Occasion Gloves", "Gift Sets", "Accessories"],
        "tools_detected": ["Google Analytics", "Meta Pixel", "Klaviyo"],
        "price_range": "$55 – $220",
        "blog_topics": ["Style Tips", "How to Customize", "Occasion Guides"],
        "social_proof": {"review_count": 410, "has_testimonials": True},
        "score": 6,
        "score_reasoning": "Niche fashion brand with Klaviyo but low repurchase frequency (custom gloves are occasional purchases) — moderate opportunity, gifting angle is strongest.",
        "snapshot": "Wing+Weft Gloves is a specialty fashion brand offering customized and fashion gloves as statement accessories. With Klaviyo active but no loyalty or review app, their main opportunity is leveraging their gifting appeal and post-purchase referral potential rather than repeat purchase frequency.",
        "pain_points": [
            "Low natural repurchase frequency for custom gloves — loyalty must be built around gifting and referrals",
            "No review display app — 410 reviews not surfaced on product pages for a considered-purchase item",
            "No referral mechanic despite custom gloves being a highly giftable, shareable product",
            "No gift messaging or gift loyalty mechanic for the holiday and occasion-gifting segments",
        ],
        "hooks": [
            "Custom gloves are a perfect gifting product — a gift-double-points mechanic would unlock holiday revenue",
            "410 reviews for a niche product is strong social proof — it needs to be displayed to convert",
            "Buyers who gift Wing+Weft gloves expose the brand to new buyers — a referral mechanic captures that",
        ],
        "channel": "email",
        "timing": "Holiday gifting season (Oct–Dec) and occasion events (Valentine's Day, Mother's Day)",
        "value_prop": "Turn your gifting audience into a referral engine — review display + gift loyalty mechanic connected to Klaviyo",
        "email_a_subject": "Wing+Weft's gifting buyers — are they referring?",
        "email_a_body": "Wing+Weft Gloves has a product that sells itself at gift-giving moments — custom, fashion-forward, and giftable. The gap: without a referral mechanic, every buyer who gifts a pair of gloves exposes Wing+Weft to a new customer you can't capture.\n\nWe add a gift-specific referral program to Klaviyo: the gift recipient gets a discount code, the buyer gets loyalty points, and Wing+Weft gets a new customer.\n\nWould a pre-holiday referral setup make sense this season?",
        "email_b_subject": "How Velvet & Thread turned gift buyers into brand advocates",
        "email_b_body": "Velvet & Thread (niche fashion accessories, similar gifting profile to Wing+Weft) launched a gift-referral program pre-holiday.\n\nResults in 90 days:\n• Referral-driven new customers: 34% of holiday revenue\n• Gift recipient conversion rate: 28%\n• Review count: +180 (from gift recipients)\n\nThe product did the heavy lifting — the mechanic just captured it. Happy to share their setup.",
        "email_c_subject": "What happens after someone receives a Wing+Weft glove as a gift?",
        "email_c_body": "Genuine question — when someone receives a Wing+Weft glove as a gift and loves it, what's the next step for them as a potential new customer?\n\nFor most fashion brands without a gift-to-referral mechanic, the answer is: nothing. They can't find the brand, or they forget.\n\nI can show you what a gift-card follow-up + referral sequence looks like for Wing+Weft. 15 minutes?",
    },

    "raawalchemy.com": {
        "description": "RAAW Alchemy — clean, natural and sustainable beauty. Science-backed formulas with ethically sourced botanical ingredients.",
        "products": ["Facial Serums", "Botanical Oils", "Cleansers", "Moisturisers", "Eye Care"],
        "tools_detected": ["Google Analytics", "Meta Pixel", "Klaviyo"],
        "price_range": "$38 – $145",
        "blog_topics": ["Ingredient Science", "Sustainability", "Clean Beauty Guide", "Botanical Research"],
        "social_proof": {"review_count": 1560, "has_testimonials": True},
        "score": 9,
        "score_reasoning": "Premium sustainable beauty brand with strong Klaviyo usage and 1,500+ reviews but no loyalty or review app — ideal fit with high-LTV clean beauty audience.",
        "snapshot": "RAAW Alchemy is a science-backed sustainable beauty brand with 1,560 reviews, active Klaviyo, and a premium price point ($38–$145). Despite strong marketing foundations they have no loyalty program or review display app — a significant gap for a brand whose sustainability positioning drives deep customer loyalty.",
        "pain_points": [
            "No loyalty program for a sustainability-driven audience that wants to feel rewarded for conscious purchasing",
            "No review display app — 1,560 reviews not visible on product pages at point of purchase",
            "No referral mechanic despite sustainability-conscious beauty buyers being strong word-of-mouth advocates",
            "No subscription mechanic for botanical serums and oils that are daily-use repurchase items",
        ],
        "hooks": [
            "Sustainability-driven beauty buyers are among the most loyal consumers — a values-aligned loyalty program is on-brand",
            "1,560 reviews is significant — a display widget on every PDP would lift conversion materially",
            "Clean beauty customers who find a brand they trust refer aggressively — you need a referral mechanic",
        ],
        "channel": "email",
        "timing": "New Year (clean beauty reset) and Earth Month (April) — peak sustainable beauty intent",
        "value_prop": "Build the values-aligned loyalty program your RAAW community deserves — review display + sustainable points connected to Klaviyo",
        "email_a_subject": "RAAW's 1,560 reviews aren't converting for you",
        "email_a_body": "RAAW Alchemy has built exceptional social proof — 1,560 reviews for a premium sustainable beauty brand. Without a review display app, most visitors never see that proof before they bounce to a competitor.\n\nWe surface your reviews on every product page and add a sustainability-themed loyalty program: points for purchases, referrals, and ideally for eco-actions (refill orders, recycled packaging returns).\n\nWant to see what a RAAW loyalty program could look like? 15 minutes.",
        "email_b_subject": "How Terre Blanche 4x'd repeat purchases with a sustainability loyalty program",
        "email_b_body": "Terre Blanche (EU sustainable beauty, similar positioning and AOV to RAAW) launched an eco-points loyalty program — customers earned extra points for choosing refill options and referring friends with shared sustainability values.\n\nIn 6 months:\n• Repeat purchase rate: 4.1x\n• Refill option uptake: 38% of orders\n• Referral-driven revenue: 31% of new sales\n\nThe loyalty mechanic reinforced their brand values rather than just incentivizing spend. Happy to share the structure.",
        "email_c_subject": "What does RAAW's customer repeat rate look like for serums and oils?",
        "email_c_body": "Quick benchmark — for premium botanical serums and oils at RAAW's price point, what percentage of customers repurchase within 90 days?\n\nFor clean beauty brands without a loyalty or subscription mechanic, it's typically 26–35%. With a values-aligned program, sustainable beauty brands typically see 58–72%.\n\nI can model what that gap is worth for RAAW's specific SKU mix. Want me to run the numbers?",
    },
}


# ── Generic fallback for any merchant not in MERCHANT_DETAILS ─────────────────

def _generic_details(domain: str, name: str, title: str) -> dict:
    """Generate minimal sample data for merchants not explicitly defined."""
    is_beauty = any(kw in title.lower() for kw in ("beauty", "skin", "spa", "loft", "glow"))
    industry = "beauty" if is_beauty else "fashion"
    return {
        "description": title,
        "products": ["Products", "Collections", "Gift Sets"],
        "tools_detected": ["Google Analytics", "Meta Pixel"],
        "price_range": "$30 – $150",
        "blog_topics": ["Style Tips", "New Arrivals"],
        "social_proof": {"review_count": 200, "has_testimonials": False},
        "score": 6,
        "score_reasoning": f"Shopify {industry} merchant with minimal tech stack — foundational email and loyalty opportunity.",
        "snapshot": f"{name} is a {industry} brand selling via Shopify. Minimal marketing tech stack suggests strong upside for email automation and loyalty.",
        "pain_points": [
            "No email marketing automation",
            "No loyalty program",
            "No review display app",
        ],
        "hooks": [
            f"No email marketing means every {industry} customer is a one-time buyer",
            "Basic tech stack leaves repeat revenue uncaptured",
        ],
        "channel": "email",
        "timing": "Seasonal launch windows",
        "value_prop": "Build a foundational email + loyalty stack to start capturing repeat revenue",
        "email_a_subject": f"{name} — a quick question",
        "email_a_body": f"Noticed {name} is running on Shopify without email automation or a loyalty program. For a {industry} brand, that means repeat purchases are being left to chance.\n\nWe set up Klaviyo + loyalty in one afternoon — cart recovery, welcome flows, and a points program. Worth a 15-minute look?",
        "email_b_subject": "How similar brands doubled repeat revenue",
        "email_b_body": f"A {industry} brand similar to {name} added email automation + loyalty last quarter. In 90 days: repeat purchase rate doubled and cart recovery added $5k/mo. Happy to share their setup.",
        "email_c_subject": f"What's {name}'s repeat purchase rate?",
        "email_c_body": f"Quick question — do you know what percentage of {name}'s customers come back for a second purchase?\n\nFor {industry} brands without email automation, it's typically under 20%. With Klaviyo + loyalty, it's usually 40–55%. I can model the gap for your store.",
    }


# ── Build output files ─────────────────────────────────────────────────────────

def build_files(df: pd.DataFrame):
    analysis_out = []
    emails_out = []
    enrichment_out = {}

    for _, row in df.iterrows():
        domain = str(row.get("domain", "")).strip()
        name = str(row.get("business_name", "") or "").strip() or domain
        title = str(row.get("title", "") or "").strip()

        if not domain:
            continue

        d = MERCHANT_DETAILS.get(domain) or _generic_details(domain, name, title)

        # ── merchant_analysis.json entry ──────────────────────────────────────
        analysis_out.append({
            "merchant": {
                "business_name": name,
                "domain": domain,
            },
            "analysis": {
                "MERCHANT SNAPSHOT": d["snapshot"],
                "PAIN POINTS DETECTED": d["pain_points"],
                "OPPORTUNITY SCORE": {
                    "score":     d["score"],
                    "reasoning": d["score_reasoning"],
                },
                "PERSONALIZATION HOOKS": d["hooks"],
                "RECOMMENDED APPROACH": {
                    "channel":    d["channel"],
                    "timing":     d["timing"],
                    "value_prop": d["value_prop"],
                },
            },
        })

        # ── merchant_emails.json entry ────────────────────────────────────────
        emails_out.append({
            "merchant": {
                "business_name": name,
                "domain": domain,
            },
            "emails": {
                "version_A": {"subject": d["email_a_subject"], "body": d["email_a_body"]},
                "version_B": {"subject": d["email_b_subject"], "body": d["email_b_body"]},
                "version_C": {"subject": d["email_c_subject"], "body": d["email_c_body"]},
            },
        })

        # ── merchant_enrichment.json entry ────────────────────────────────────
        enrichment_out[domain] = {
            "description":    d["description"],
            "products":       d["products"],
            "tools_detected": d["tools_detected"],
            "price_range":    d["price_range"],
            "blog_topics":    d["blog_topics"],
            "social_proof":   d["social_proof"],
            "source":         "sample",
        }

    return analysis_out, emails_out, enrichment_out


def main():
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found.")
        print("Run filter_shopify_merchants.py first, or place shopify_merchants.csv in this folder.")
        return

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.lower()
    print(f"Loaded {len(df)} merchants from {CSV_PATH.name}")

    analysis, emails, enrichment = build_files(df)

    files = {
        DIR / "merchant_analysis.json":   analysis,
        DIR / "merchant_emails.json":     emails,
        DIR / "merchant_enrichment.json": enrichment,
    }

    for path, data in files.items():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  OK {path.name}  ({len(data) if isinstance(data, list) else len(data)} entries)")

    print(f"\nSample data created for {len(analysis)} merchants from {CSV_PATH.name}.")
    print("Run:  python dashboard.py   then open http://localhost:5000")


if __name__ == "__main__":
    main()
