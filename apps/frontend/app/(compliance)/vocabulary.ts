/**
 * Compliance persona vocabulary.
 * Maps generic term keys to compliance-specific labels.
 */
export const complianceVocabulary: Record<string, string> = {
  // Dashboard
  compliance_rate: "Overall Compliance Rate",
  subject: "Compliance Item",
  subjects: "Compliance Items",
  evaluation: "Compliance Audit",
  evaluations: "Compliance Audits",
  violation: "Non-Compliance",
  violations: "Non-Compliances",
  rule: "Regulation",
  rules: "Regulations",

  // Actions
  submit_for_review: "Submit for Audit",
  approve: "Mark Compliant",
  deny: "Flag Non-Compliant",

  // Domain terms
  domain_name: "Compliance",
  landing_title: "Cross-Domain Compliance Summary",
  primary_action: "View Audit Log",
  queue_name: "Audit Queue",
  item_name: "Audit Item",
  items_name: "Audit Items",
};
