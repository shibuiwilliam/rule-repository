"use client";

const COMPLIANCE_CHECKPOINTS = [
  {
    id: 1,
    regulation: "景品表示法 (Act against Unjustifiable Premiums and Misleading Representations)",
    description:
      "Prohibits misleading representations about products and services. All advertising claims must be substantiated and not create false impressions of superior quality or value.",
    severity: "critical",
    checks: [
      "No優良誤認表示 (misleading superior quality claims)",
      "No有利誤認表示 (misleading advantageous claims)",
      "Proper disclosure of conditions and limitations",
      "Substantiation for all comparative claims",
    ],
  },
  {
    id: 2,
    regulation: "薬機法 (Act on Securing Quality, Efficacy and Safety of Products)",
    description:
      "Regulates advertising of pharmaceuticals, medical devices, cosmetics, and quasi-drugs. Restricts health-related claims in non-medical product advertising.",
    severity: "critical",
    checks: [
      "No unapproved efficacy or effect claims",
      "No before/after imagery implying medical effects",
      "Proper categorization of product claims (cosmetic vs. quasi-drug vs. pharmaceutical)",
      "Required disclaimers for health-related products",
    ],
  },
  {
    id: 3,
    regulation: "特定商取引法 (Specified Commercial Transactions Act)",
    description:
      "Governs mail-order sales, telemarketing, and online transactions. Requires specific disclosures in advertising materials.",
    severity: "high",
    checks: [
      "Price and payment terms clearly stated",
      "Return/cancellation policy disclosed",
      "Seller identity and contact information included",
      "Delivery timeline and conditions specified",
    ],
  },
  {
    id: 4,
    regulation: "著作権法 (Copyright Act)",
    description:
      "Protects creative works used in advertising. All third-party content must be properly licensed or fall under fair use exceptions.",
    severity: "high",
    checks: [
      "Licensed stock imagery and fonts",
      "Music and audio rights cleared",
      "User-generated content permissions obtained",
      "Proper attribution where required",
    ],
  },
  {
    id: 5,
    regulation: "個人情報保護法 (Act on Protection of Personal Information)",
    description:
      "Governs the use of personal data in targeted advertising and customer communications.",
    severity: "high",
    checks: [
      "Consent obtained for personalized advertising",
      "Opt-out mechanism provided",
      "Data usage purpose clearly communicated",
      "Third-party data sharing disclosed",
    ],
  },
];

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
};

export default function AdCompliancePage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Ad Compliance</h1>
        <p className="mt-1 text-sm text-gray-500">
          Advertising regulation rules and compliance checkpoints applicable to marketing
          creatives, campaigns, and communications
        </p>
      </div>

      <div className="rounded-xl border bg-blue-50 p-4 text-sm text-blue-800">
        All advertising materials must be reviewed against applicable regulations before
        publication. Critical violations may result in regulatory action, fines, or mandatory
        corrective advertising.
      </div>

      <div className="space-y-4">
        {COMPLIANCE_CHECKPOINTS.map((cp) => (
          <div key={cp.id} className="rounded-xl border bg-white p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-semibold text-gray-900">{cp.regulation}</h2>
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[cp.severity] ?? "bg-gray-100 text-gray-700"}`}
                  >
                    {cp.severity}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-600">{cp.description}</p>
              </div>
            </div>
            <ul className="mt-3 space-y-1">
              {cp.checks.map((check, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-0.5 text-gray-400">&#x2022;</span>
                  {check}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
