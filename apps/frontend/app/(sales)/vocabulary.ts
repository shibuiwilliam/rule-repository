/**
 * Sales persona vocabulary.
 * Maps generic term keys to sales-specific labels.
 */
export const salesVocabulary: Record<string, string> = {
  // Dashboard
  compliance_rate: "Pricing Compliance Rate",
  subject: "Deal",
  subjects: "Deals",
  evaluation: "Deal Review",
  evaluations: "Deal Reviews",
  violation: "Pricing Exception",
  violations: "Pricing Exceptions",
  rule: "Pricing Policy",
  rules: "Pricing Policies",

  // Actions
  submit_for_review: "Submit Deal",
  approve: "Approve Deal",
  deny: "Escalate",

  // Domain terms
  domain_name: "Sales",
  landing_title: "Deal & Discount Review",
  primary_action: "Review Proposed Discounts",
  queue_name: "Deal Queue",
  item_name: "Deal",
  items_name: "Deals",
};
