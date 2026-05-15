/**
 * HR persona vocabulary.
 * Maps generic term keys to human-resources-specific labels.
 */
export const hrVocabulary: Record<string, string> = {
  // Dashboard
  compliance_rate: "Policy Compliance Rate",
  subject: "Employee Event",
  subjects: "Employee Events",
  evaluation: "Compliance Check",
  evaluations: "Compliance Checks",
  violation: "Policy Violation",
  violations: "Policy Violations",
  rule: "HR Policy",
  rules: "HR Policies",

  // Actions
  submit_for_review: "Submit Event",
  approve: "Approve",
  deny: "Reject",

  // Domain terms
  domain_name: "Human Resources",
  landing_title: "Employee Event Compliance",
  primary_action: "Review Pending Events",
  queue_name: "Event Queue",
  item_name: "Event",
  items_name: "Events",
};
