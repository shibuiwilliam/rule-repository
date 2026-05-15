/**
 * Finance persona vocabulary.
 * Maps generic term keys to finance-specific labels.
 */
export const financeVocabulary: Record<string, string> = {
  // Dashboard
  compliance_rate: "Expense Compliance Rate",
  subject: "Transaction",
  subjects: "Transactions",
  evaluation: "Expense Review",
  evaluations: "Expense Reviews",
  violation: "Policy Exception",
  violations: "Policy Exceptions",
  rule: "Financial Control",
  rules: "Financial Controls",

  // Actions
  submit_for_review: "Submit for Approval",
  approve: "Approve",
  deny: "Reject",

  // Domain terms
  domain_name: "Finance",
  landing_title: "Transaction Approval Queue",
  primary_action: "Review Expenses",
  queue_name: "Approval Queue",
  item_name: "Transaction",
  items_name: "Transactions",
};
