/**
 * Legal persona vocabulary.
 * Maps generic term keys to legal-specific labels.
 */
export const legalVocabulary: Record<string, string> = {
  // Dashboard
  compliance_rate: "Contract Compliance Rate",
  subject: "Contract",
  subjects: "Contracts",
  evaluation: "Contract Review",
  evaluations: "Contract Reviews",
  violation: "Clause Issue",
  violations: "Clause Issues",
  rule: "Clause Requirement",
  rules: "Clause Requirements",

  // Actions
  submit_for_review: "Submit for Review",
  approve: "Approve",
  deny: "Flag for Revision",

  // Domain terms
  domain_name: "Legal",
  landing_title: "Contract Review Queue",
  primary_action: "Review Contract",
  queue_name: "Contract Queue",
  item_name: "Contract",
  items_name: "Contracts",
};
