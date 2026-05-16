"use client";

interface BrandRule {
  id: number;
  category: string;
  title: string;
  description: string;
  modality: "MUST" | "MUST_NOT" | "SHOULD";
  examples: string[];
}

const BRAND_RULES: BrandRule[] = [
  {
    id: 1,
    category: "Logo Usage",
    title: "Minimum clear space around logo",
    description:
      "The primary logo must maintain a clear space equal to the height of the logomark on all sides. No other graphical elements, text, or edges may encroach on this space.",
    modality: "MUST",
    examples: [
      "Logo placed with adequate padding in email headers",
      "Violation: logo cropped at the edge of a social media banner",
    ],
  },
  {
    id: 2,
    category: "Logo Usage",
    title: "Do not alter logo colors or proportions",
    description:
      "The logo must not be stretched, rotated, recolored, or modified in any way. Only approved color variants (full color, monochrome white, monochrome black) are permitted.",
    modality: "MUST_NOT",
    examples: [
      "Using the monochrome white variant on dark backgrounds",
      "Violation: applying a gradient overlay to the full-color logo",
    ],
  },
  {
    id: 3,
    category: "Color Palette",
    title: "Use approved brand colors only",
    description:
      "All marketing materials must use colors from the approved brand palette. Primary: #1A73E8 (Blue), #202124 (Dark Gray). Secondary: #34A853 (Green), #FBBC04 (Yellow), #EA4335 (Red). Neutral: #F8F9FA, #DADCE0, #5F6368.",
    modality: "MUST",
    examples: [
      "Landing page using primary blue for CTAs and dark gray for body text",
      "Violation: using an off-brand purple as a primary accent color",
    ],
  },
  {
    id: 4,
    category: "Color Palette",
    title: "Maintain sufficient contrast ratios",
    description:
      "Text over colored backgrounds must meet WCAG 2.1 AA contrast requirements: at least 4.5:1 for normal text and 3:1 for large text.",
    modality: "MUST",
    examples: [
      "White text (#FFFFFF) on primary blue (#1A73E8) passes at 4.6:1",
      "Violation: light gray text on white background at 2.1:1 ratio",
    ],
  },
  {
    id: 5,
    category: "Tone of Voice",
    title: "Use active, clear, and confident language",
    description:
      "Marketing copy should be written in active voice, avoid jargon, and convey confidence without arrogance. Sentences should be concise and scannable.",
    modality: "SHOULD",
    examples: [
      "\"Start building in minutes\" (active, clear, confident)",
      "Violation: \"It is possible that utilization of our solution may potentially yield results\" (passive, vague)",
    ],
  },
  {
    id: 6,
    category: "Tone of Voice",
    title: "Do not use superlatives without substantiation",
    description:
      "Claims such as \"best\", \"fastest\", \"#1\", or \"industry-leading\" must be backed by verifiable data or third-party validation. Unsubstantiated superlatives violate both brand guidelines and advertising regulations.",
    modality: "MUST_NOT",
    examples: [
      "\"Rated #1 by Gartner in 2025\" (substantiated with source)",
      "Violation: \"The best platform on the market\" (no supporting evidence)",
    ],
  },
  {
    id: 7,
    category: "Typography",
    title: "Use approved typefaces",
    description:
      "All marketing materials must use the approved typeface family. Primary: Inter for digital, Noto Sans JP for Japanese content. Fallback: system sans-serif. Display sizes follow the type scale defined in the brand guide.",
    modality: "MUST",
    examples: [
      "Website headings set in Inter Bold at 32px / 40px line height",
      "Violation: using a decorative script font for body copy in a product brochure",
    ],
  },
];

const MODALITY_STYLES: Record<string, string> = {
  MUST: "bg-blue-100 text-blue-800",
  MUST_NOT: "bg-red-100 text-red-800",
  SHOULD: "bg-yellow-100 text-yellow-800",
};

export default function BrandRulesPage() {
  const categories = [...new Set(BRAND_RULES.map((r) => r.category))];

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Brand Rules</h1>
        <p className="mt-1 text-sm text-gray-500">
          Brand guideline rules governing logo usage, color palette, typography, and tone of
          voice across all marketing materials
        </p>
      </div>

      {categories.map((category) => (
        <div key={category} className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-800">{category}</h2>
          {BRAND_RULES.filter((r) => r.category === category).map((rule) => (
            <div key={rule.id} className="rounded-xl border bg-white p-5">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-semibold text-gray-900">{rule.title}</h3>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${MODALITY_STYLES[rule.modality]}`}
                >
                  {rule.modality}
                </span>
              </div>
              <p className="mt-1 text-sm text-gray-600">{rule.description}</p>
              <div className="mt-3 space-y-1">
                {rule.examples.map((ex, i) => (
                  <p key={i} className="text-xs text-gray-500">
                    {ex}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
