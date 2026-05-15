/**
 * Engineering persona vocabulary.
 * Maps generic term keys to engineering-specific labels.
 */
export const engineeringVocabulary: Record<string, string> = {
  // Dashboard
  compliance_rate: "Code Compliance Rate",
  subject: "Code Change",
  subjects: "Code Changes",
  evaluation: "Code Review",
  evaluations: "Code Reviews",
  violation: "Violation",
  violations: "Violations",
  rule: "Rule",
  rules: "Rules",

  // Actions
  submit_for_review: "Submit for Review",
  approve: "Approve",
  deny: "Deny",

  // Domain terms
  domain_name: "Engineering",
  landing_title: "Code Compliance Dashboard",
  primary_action: "Run Check on PR",
  queue_name: "Review Queue",
  item_name: "Pull Request",
  items_name: "Pull Requests",
};
