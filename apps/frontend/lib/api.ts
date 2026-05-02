/**
 * Typed API client for the Rule Repository backend.
 */

// Server-side (SSR) uses internal Docker network; client-side uses public URL
const API_BASE =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000");

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectList {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
}

export const getProjects = (page = 1, pageSize = 50) =>
  apiFetch<ProjectList>(`/api/v1/projects?page=${page}&page_size=${pageSize}`);

export const getProject = (id: string) => apiFetch<Project>(`/api/v1/projects/${id}`);

export const createProject = (data: { name: string; description?: string }) =>
  apiFetch<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateProject = (id: string, data: { name?: string; description?: string }) =>
  apiFetch<Project>(`/api/v1/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Rule {
  id: string;
  project_id: string | null;
  statement: string;
  modality: string;
  severity: string;
  status: string;
  scope: string[];
  tags: string[];
  rationale: string;
  context: string;
  preconditions: string[];
  exceptions: string[];
  following_examples: string[];
  violation_examples: string[];
  source_refs: Record<string, unknown>[];
  effective_period: { valid_from: string | null; valid_until: string | null };
  governance: { owner: string; approvers: string[] };
  created_at: string;
  updated_at: string;
}

export interface RuleList {
  items: Rule[];
  total: number;
  page: number;
  page_size: number;
}

export interface SearchResultItem {
  rule: Rule;
  score: number;
}

export interface SearchResult {
  items: SearchResultItem[];
  total: number;
  page: number;
  page_size: number;
  query: string;
}

export interface Revision {
  id: string;
  rule_id: string;
  revision_number: number;
  statement: string;
  modality: string;
  severity: string;
  status: string;
  changed_by: string;
  change_note: string;
  created_at: string;
}

export interface Relationship {
  source_id: string;
  target_id: string;
  relationship_type: string;
  created_at: string;
  created_by: string;
}

export interface GraphData {
  nodes: { id: string; properties: Record<string, unknown> }[];
  edges: { source: string; target: string; type: string }[];
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// Rules
export const getRules = (page = 1, pageSize = 20, projectId?: string) => {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (projectId) params.set("project_id", projectId);
  return apiFetch<RuleList>(`/api/v1/rules?${params}`);
};

export const getRule = (id: string) => apiFetch<Rule>(`/api/v1/rules/${id}`);

export const createRule = (data: Record<string, unknown>, projectId?: string) => {
  const params = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<Rule>(`/api/v1/rules${params}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
};

export const updateRule = (id: string, data: Record<string, unknown>) =>
  apiFetch<Rule>(`/api/v1/rules/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const retireRule = (id: string) =>
  apiFetch<Rule>(`/api/v1/rules/${id}/retire`, { method: "POST" });

export const getRevisions = (id: string) =>
  apiFetch<Revision[]>(`/api/v1/rules/${id}/revisions`);

export const getRelationships = (id: string) =>
  apiFetch<Relationship[]>(`/api/v1/rules/${id}/relationships`);

export const getGraph = (id: string, depth = 1) =>
  apiFetch<GraphData>(`/api/v1/rules/${id}/graph?depth=${depth}`);

export const createRelationship = (data: {
  source_id: string;
  target_id: string;
  relationship_type: string;
}) => apiFetch<Relationship>("/api/v1/relationships", {
  method: "POST",
  body: JSON.stringify(data),
});

export const deleteRelationship = (sourceId: string, targetId: string, relationshipType: string) => {
  const params = new URLSearchParams({ source_id: sourceId, target_id: targetId, relationship_type: relationshipType });
  return apiFetch<void>(`/api/v1/relationships?${params}`, { method: "DELETE" });
};

// Search
export const searchFulltext = (query: string, page = 1, pageSize = 20, projectId?: string) =>
  apiFetch<SearchResult>("/api/v1/search/fulltext", {
    method: "POST",
    body: JSON.stringify({ query, page, page_size: pageSize, project_id: projectId }),
  });

export const searchHybrid = (query: string, page = 1, pageSize = 20, projectId?: string) =>
  apiFetch<SearchResult>("/api/v1/search/hybrid", {
    method: "POST",
    body: JSON.stringify({ query, page, page_size: pageSize, project_id: projectId }),
  });

export const searchVector = (query: string, page = 1, pageSize = 20, projectId?: string) =>
  apiFetch<SearchResult>("/api/v1/search/vector", {
    method: "POST",
    body: JSON.stringify({ query, page, page_size: pageSize, project_id: projectId }),
  });

// Intent
export const askIntent = (query: string) =>
  apiFetch<{ intent: string; result: unknown; explanation: string }>(
    "/api/v1/intent",
    {
      method: "POST",
      body: JSON.stringify({ query }),
    },
  );

// Documents
export interface DocumentInfo {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  uploaded_by: string;
}

export const getDocument = (id: string): Promise<DocumentInfo> =>
  apiFetch<DocumentInfo>(`/api/v1/documents/${id}`);

export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
};

export const extractRules = (documentId: string) =>
  apiFetch<{
    extraction_id: string;
    candidates: Record<string, unknown>[];
  }>(`/api/v1/documents/${documentId}/extract`, { method: "POST" });

// ---------------------------------------------------------------------------
// Discovery
// ---------------------------------------------------------------------------

export interface DiscoveryCandidate {
  id: string;
  statement: string;
  modality: string;
  severity: string;
  scope: string[];
  tags: string[];
  rationale: string | null;
  source_type: string;
  source_evidence: string | null;
  confidence: number;
  status: string;
}

export interface ScanStatus {
  scan_id: string;
  status: "pending" | "running" | "completed" | "failed";
  total_candidates: number;
  error: string | null;
}

export const startDiscoveryScan = (
  sources: string[],
  fileContents: Record<string, string>,
  repository?: string,
  projectId?: string,
) =>
  apiFetch<{ scan_id: string }>("/api/v1/discover/scan", {
    method: "POST",
    body: JSON.stringify({ sources, file_contents: fileContents, repository, project_id: projectId }),
  });

export const getScanStatus = (scanId: string) =>
  apiFetch<ScanStatus>(`/api/v1/discover/scan/${scanId}`);

export const getDiscoveryCandidates = (scanId: string) =>
  apiFetch<DiscoveryCandidate[]>(
    `/api/v1/discover/candidates?scan_id=${scanId}`,
  );

export const approveCandidate = (candidateId: string) =>
  apiFetch<{ rule_id: string }>(
    `/api/v1/discover/candidates/${candidateId}/approve`,
    { method: "POST" },
  );

export const dismissCandidate = (candidateId: string) =>
  apiFetch<{ status: string }>(
    `/api/v1/discover/candidates/${candidateId}/dismiss`,
    { method: "POST" },
  );

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export interface Correction {
  id: string;
  analysis_type: string | null;
  matched_rule_ids: string[];
  candidate_statement: string | null;
  candidate_modality: string | null;
  candidate_severity: string | null;
  confidence: number | null;
  status: string;
  file_paths: string[];
  repository: string | null;
  created_at: string;
}

export interface FeedbackStats {
  total_corrections: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  rules_created: number;
  top_violated_rules: Array<{ rule_id: string; count: number }>;
}

export async function submitCorrection(data: {
  original_diff: string;
  corrected_diff: string;
  file_paths?: string[];
  repository?: string;
}) {
  return apiFetch('/api/v1/feedback/corrections', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getCorrections(status?: string, page = 1, pageSize = 20, projectId?: string) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set('status', status);
  if (projectId) params.set('project_id', projectId);
  return apiFetch<{ items: Correction[]; total: number }>(`/api/v1/feedback/corrections?${params}`);
}

export async function approveCorrection(correctionId: string) {
  return apiFetch(`/api/v1/feedback/corrections/${correctionId}/approve`, { method: 'POST' });
}

export async function dismissCorrection(correctionId: string) {
  return apiFetch(`/api/v1/feedback/corrections/${correctionId}/dismiss`, { method: 'POST' });
}

export async function getFeedbackStats(projectId?: string): Promise<FeedbackStats> {
  const params = projectId ? `?project_id=${projectId}` : '';
  return apiFetch(`/api/v1/feedback/stats${params}`);
}

// ---------------------------------------------------------------------------
// Federation
// ---------------------------------------------------------------------------

export interface Federation {
  id: string;
  name: string;
  level: string;
  parent_id: string | null;
  description: string | null;
  default_scope: string[];
  created_at: string;
  children?: Federation[];
}

export interface FederationDetail extends Federation {
  rules: Array<{
    rule_id: string;
    statement: string;
    modality: string;
    severity: string;
    override_parent_rule_id: string | null;
  }>;
}

export interface EffectiveRule {
  rule_id: string;
  statement: string;
  modality: string;
  severity: string;
  source_federation_id: string;
  source_federation_name: string;
  overrides: string | null;
}

export async function getFederations(): Promise<Federation[]> {
  return apiFetch('/api/v1/federations');
}

export async function createFederation(data: {
  name: string;
  level: string;
  parent_id?: string | null;
  description?: string;
  default_scope?: string[];
}) {
  return apiFetch('/api/v1/federations', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getFederation(id: string): Promise<FederationDetail> {
  return apiFetch(`/api/v1/federations/${id}`);
}

export async function getEffectiveRules(federationId: string): Promise<EffectiveRule[]> {
  return apiFetch(`/api/v1/federations/${federationId}/effective-rules`);
}

export async function addRuleToFederation(federationId: string, ruleId: string, overrideParentRuleId?: string) {
  return apiFetch(`/api/v1/federations/${federationId}/rules`, {
    method: 'POST',
    body: JSON.stringify({ rule_id: ruleId, override_parent_rule_id: overrideParentRuleId }),
  });
}

export async function removeRuleFromFederation(federationId: string, ruleId: string) {
  return apiFetch(`/api/v1/federations/${federationId}/rules/${ruleId}`, { method: 'DELETE' });
}

export interface FederationDiff {
  federation_a: string;
  federation_b: string;
  only_in_a: EffectiveRule[];
  only_in_b: EffectiveRule[];
  common: EffectiveRule[];
}

export async function diffFederations(idA: string, idB: string): Promise<FederationDiff> {
  return apiFetch(`/api/v1/federations/${idA}/diff/${idB}`);
}

// ---------------------------------------------------------------------------
// Playground
// ---------------------------------------------------------------------------

export interface PlaygroundResult {
  verdict: string;
  confidence: number;
  reasoning: string;
  issue_description: string;
  fix_suggestion: string | null;
  locations: Array<{ file_path: string; start_line: number | null; function_name: string | null }>;
}

export interface TestCase {
  id: string;
  name: string;
  sample_input: string;
  input_type: string;
  expected_verdict: string;
  last_result: string | null;
  passing: boolean | null;
  last_run_at: string | null;
}

export interface TestRunResult {
  total: number;
  passing: number;
  failing: number;
  results: TestCase[];
}

export async function playgroundEvaluate(data: {
  rule_statement: string;
  rule_modality?: string;
  rule_severity?: string;
  sample_code?: string;
  sample_facts?: Record<string, unknown>;
}): Promise<PlaygroundResult> {
  return apiFetch('/api/v1/playground/evaluate', { method: 'POST', body: JSON.stringify(data) });
}

export async function getTestCases(ruleId: string): Promise<TestCase[]> {
  return apiFetch(`/api/v1/playground/rules/${ruleId}/test-cases`);
}

export async function createTestCase(ruleId: string, data: { name: string; sample_input: string; input_type?: string; expected_verdict: string }) {
  return apiFetch(`/api/v1/playground/rules/${ruleId}/test-cases`, { method: 'POST', body: JSON.stringify(data) });
}

export async function runTestSuite(ruleId: string): Promise<TestRunResult> {
  return apiFetch(`/api/v1/playground/rules/${ruleId}/test-cases/run`, { method: 'POST' });
}

export async function generateTestCases(ruleId: string, count = 6): Promise<TestCase[]> {
  return apiFetch(`/api/v1/playground/rules/${ruleId}/test-cases/generate`, { method: 'POST', body: JSON.stringify({ count }) });
}

export async function deleteTestCase(ruleId: string, testCaseId: string) {
  return apiFetch(`/api/v1/playground/rules/${ruleId}/test-cases/${testCaseId}`, { method: 'DELETE' });
}

export interface SuggestInputResult {
  sample_input: string;
  description: string;
}

export async function suggestInput(data: {
  rule_id?: string;
  rule_statement?: string;
  rule_modality?: string;
  rule_severity?: string;
  input_mode?: string;
  violating?: boolean;
}): Promise<SuggestInputResult> {
  return apiFetch('/api/v1/playground/suggest-input', { method: 'POST', body: JSON.stringify(data) });
}

// ---------------------------------------------------------------------------
// Home Dashboard Summary
// ---------------------------------------------------------------------------

export interface ComplianceTrendPoint {
  date: string;
  total: number;
  allow_count: number;
  compliance_rate: number;
}

export interface HomeSummary {
  compliance_rate: number;
  compliance_trend: ComplianceTrendPoint[];
  total_rules: number;
  rules_by_status: Record<string, number>;
  top_violated_rules: Array<{ rule_id: string; violation_count: number; rule_statement?: string; effectiveness_score?: number | null }>;
  recent_corrections: Array<{
    id: string;
    status: string;
    candidate_statement: string | null;
    analysis_type: string | null;
    created_at: string;
  }>;
  pending_actions: {
    rules_pending_review: number;
    corrections_pending: number;
    active_alerts: number;
  };
}

export async function getHomeSummary(projectId?: string): Promise<HomeSummary> {
  const params = projectId ? `?project_id=${projectId}` : '';
  return apiFetch(`/api/v1/intelligence/summary${params}`);
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export interface Alert {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  description: string | null;
  rule_id: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

export async function getAlerts(status?: string, page = 1, pageSize = 20, projectId?: string) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set('status', status);
  if (projectId) params.set('project_id', projectId);
  return apiFetch(`/api/v1/alerts?${params}`);
}

export async function acknowledgeAlert(alertId: string) {
  return apiFetch(`/api/v1/alerts/${alertId}/acknowledge`, { method: 'POST' });
}

export async function resolveAlert(alertId: string) {
  return apiFetch(`/api/v1/alerts/${alertId}/resolve`, { method: 'POST' });
}

// ---------------------------------------------------------------------------
// Intelligence
// ---------------------------------------------------------------------------

export interface CacheStats {
  cache_hits: number;
  cache_misses: number;
  hit_rate: number;
  period_days: number;
}

export interface TopViolatedRule {
  rule_id: string;
  violation_count: number;
}

export interface DashboardSummary {
  total_rules: number;
  avg_health_score: number;
  total_evaluations_30d: number;
  verdict_distribution: Record<string, number>;
  active_drift_alerts: number;
  open_recommendations: number;
  health_distribution: Record<string, number>;
  cache_stats: CacheStats;
  top_violated_rules: TopViolatedRule[];
}

export interface HealthScore {
  rule_id: string;
  overall_score: number;
  completeness: number;
  clarity: number;
  test_coverage: number;
  freshness: number;
  activity: number;
  owner_engagement: number;
  issues: string[];
  computed_at: string | null;
}

export interface HealthScoreList {
  items: HealthScore[];
  total: number;
  page: number;
  page_size: number;
}

export interface CorpusAnalytics {
  total_evaluations: number;
  verdict_distribution: Record<string, number>;
  avg_latency_ms: number;
}

export interface IntelligenceRecommendation {
  id: string;
  rule_id: string;
  type: string;
  title: string;
  description: string;
  suggested_change: string | null;
  related_rule_ids: string[];
  priority: string;
  status: string;
  created_at: string | null;
}

export interface RecommendationList {
  items: IntelligenceRecommendation[];
  total: number;
  page: number;
  page_size: number;
}

export async function getIntelligenceDashboard(projectId?: string): Promise<DashboardSummary> {
  const params = projectId ? `?project_id=${projectId}` : '';
  return apiFetch(`/api/v1/intelligence/dashboard${params}`);
}

export async function getHealthScores(
  page = 1,
  pageSize = 20,
  sortBy = 'overall_score',
  projectId?: string,
): Promise<HealthScoreList> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    sort_by: sortBy,
  });
  if (projectId) params.set('project_id', projectId);
  return apiFetch(`/api/v1/intelligence/health?${params}`);
}

export async function getRuleHealth(ruleId: string): Promise<HealthScore> {
  return apiFetch(`/api/v1/intelligence/health/${ruleId}`);
}

export async function getCorpusAnalytics(periodDays = 30, projectId?: string): Promise<CorpusAnalytics> {
  const params = new URLSearchParams({ period_days: String(periodDays) });
  if (projectId) params.set('project_id', projectId);
  return apiFetch(`/api/v1/intelligence/analytics?${params}`);
}

export async function getIntelligenceRecommendations(
  status = 'open',
  page = 1,
  pageSize = 20,
  projectId?: string,
): Promise<RecommendationList> {
  const params = new URLSearchParams({
    status,
    page: String(page),
    page_size: String(pageSize),
  });
  if (projectId) params.set('project_id', projectId);
  return apiFetch(`/api/v1/intelligence/recommendations?${params}`);
}

// ---------------------------------------------------------------------------
// Snapshots
// ---------------------------------------------------------------------------

export interface Snapshot {
  id: string;
  name: string;
  description: string | null;
  scope_filter: string[];
  rule_count: number;
  created_by: string;
  created_at: string;
}

export interface Deployment {
  id: string;
  snapshot_id: string;
  environment: string;
  active: boolean;
  deployed_by: string;
  deployed_at: string;
  rolled_back_at: string | null;
}

export interface SimulateResult {
  total_replayed: number;
  rules_added: number;
  rules_removed: number;
  risk_assessment: string;
}

export async function createSnapshot(data: { name: string; scope_filter?: string[]; description?: string; project_id?: string }) {
  const { project_id, ...body } = data;
  const params = project_id ? `?project_id=${project_id}` : '';
  return apiFetch(`/api/v1/snapshots${params}`, { method: 'POST', body: JSON.stringify(body) });
}

export async function getSnapshots(projectId?: string): Promise<Snapshot[]> {
  const params = projectId ? `?project_id=${projectId}` : '';
  return apiFetch(`/api/v1/snapshots${params}`);
}

export async function deploySnapshot(snapshotId: string, environment: string) {
  return apiFetch(`/api/v1/snapshots/${snapshotId}/deploy`, { method: 'POST', body: JSON.stringify({ environment }) });
}

export async function rollbackSnapshot(snapshotId: string) {
  return apiFetch(`/api/v1/snapshots/${snapshotId}/rollback`, { method: 'POST' });
}

export async function simulateSnapshot(snapshotId: string, compareTo = 'production', sampleSize = 100): Promise<SimulateResult> {
  return apiFetch(`/api/v1/snapshots/${snapshotId}/simulate`, { method: 'POST', body: JSON.stringify({ compare_to: compareTo, sample_size: sampleSize }) });
}

export async function getDeployments(): Promise<Deployment[]> {
  return apiFetch('/api/v1/snapshots/deployments');
}

// ---------------------------------------------------------------------------
// Proposals (Phase 6a: Collaborative Governance)
// ---------------------------------------------------------------------------

export interface ProposalComment {
  id: string;
  proposal_id: string;
  parent_comment_id: string | null;
  author_id: string;
  body: string;
  comment_type: string;
  suggestion_spec: Record<string, unknown> | null;
  resolved: boolean;
  created_at: string;
}

export interface Proposal {
  id: string;
  project_id: string | null;
  proposal_type: string;
  status: string;
  author_id: string;
  title: string;
  description: string;
  change_spec: Record<string, unknown>;
  target_rule_ids: string[];
  conflict_analysis: Record<string, unknown> | null;
  impact_preview: Record<string, unknown> | null;
  required_approvers: string[];
  approval_votes: Array<{ user_id: string; vote: string; condition?: string | null; timestamp: string }>;
  comments: ProposalComment[];
  enacted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProposalList {
  items: Proposal[];
  total: number;
  page: number;
  page_size: number;
}

export async function getProposals(
  status?: string,
  page = 1,
  pageSize = 20,
  projectId?: string,
): Promise<ProposalList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set('status', status);
  if (projectId) params.set('project_id', projectId);
  return apiFetch(`/api/v1/proposals?${params}`);
}

export async function getProposal(id: string): Promise<Proposal> {
  return apiFetch(`/api/v1/proposals/${id}`);
}

export async function createProposal(data: {
  proposal_type: string;
  title: string;
  description?: string;
  target_rule_ids?: string[];
  change_spec?: Record<string, unknown>;
  required_approvers?: string[];
}, projectId?: string, authorId = 'system'): Promise<Proposal> {
  const params = new URLSearchParams();
  if (projectId) params.set('project_id', projectId);
  if (authorId) params.set('author_id', authorId);
  return apiFetch(`/api/v1/proposals?${params}`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProposal(id: string, data: {
  title?: string;
  description?: string;
  target_rule_ids?: string[];
  change_spec?: Record<string, unknown>;
  required_approvers?: string[];
}): Promise<Proposal> {
  return apiFetch(`/api/v1/proposals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function submitProposal(id: string): Promise<Proposal> {
  return apiFetch(`/api/v1/proposals/${id}/submit`, { method: 'POST' });
}

export async function voteOnProposal(id: string, vote: string, voterId = 'system', condition?: string): Promise<Proposal> {
  const params = new URLSearchParams({ voter_id: voterId });
  return apiFetch(`/api/v1/proposals/${id}/vote?${params}`, {
    method: 'POST',
    body: JSON.stringify({ vote, condition }),
  });
}

export async function enactProposal(id: string, actor = 'system'): Promise<Proposal> {
  const params = new URLSearchParams({ actor });
  return apiFetch(`/api/v1/proposals/${id}/enact?${params}`, { method: 'POST' });
}

export async function revertProposal(id: string): Promise<Proposal> {
  return apiFetch(`/api/v1/proposals/${id}/revert`, { method: 'POST' });
}

export async function closeProposal(id: string): Promise<Proposal> {
  return apiFetch(`/api/v1/proposals/${id}/close`, { method: 'POST' });
}

export async function addProposalComment(proposalId: string, data: {
  body: string;
  parent_comment_id?: string | null;
  comment_type?: string;
  suggestion_spec?: Record<string, unknown> | null;
}): Promise<ProposalComment> {
  return apiFetch(`/api/v1/proposals/${proposalId}/comments`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function refreshProposalAnalysis(id: string): Promise<Proposal> {
  return apiFetch(`/api/v1/proposals/${id}/analyze`, { method: 'POST' });
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export interface AppNotification {
  id: string;
  user_id: string;
  proposal_id: string | null;
  notification_type: string;
  title: string;
  body: string;
  read: boolean;
  created_at: string;
}

export interface NotificationList {
  items: AppNotification[];
  total: number;
  unread_count: number;
}

export async function getNotifications(userId: string, unreadOnly = false, page = 1): Promise<NotificationList> {
  const params = new URLSearchParams({ user_id: userId, page: String(page) });
  if (unreadOnly) params.set('unread_only', 'true');
  return apiFetch(`/api/v1/proposals/notifications/inbox?${params}`);
}

export async function markNotificationRead(id: string): Promise<AppNotification> {
  return apiFetch(`/api/v1/proposals/notifications/${id}/read`, { method: 'PATCH' });
}

export async function markAllNotificationsRead(userId: string): Promise<{ marked_read: number }> {
  const params = new URLSearchParams({ user_id: userId });
  return apiFetch(`/api/v1/proposals/notifications/mark-all-read?${params}`, { method: 'POST' });
}

// ---------------------------------------------------------------------------
// Agent Governance (Phase 6b)
// ---------------------------------------------------------------------------

export interface AgentProfile {
  agent_id: string;
  display_name: string;
  agent_type: string;
  capabilities: string[];
  trust_level: string;
  compliance_rate_30d: number;
  violation_patterns: Record<string, unknown>;
  strength_areas: string[];
  weakness_areas: string[];
  can_propose_rules: boolean;
  can_vote_on_proposals: boolean;
  max_auto_fix_severity: string;
  mastered_rules_count: number;
  created_at: string;
  updated_at: string;
}

export interface AgentList {
  items: AgentProfile[];
  total: number;
  page: number;
  page_size: number;
}

export async function getAgents(page = 1, pageSize = 20): Promise<AgentList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return apiFetch(`/api/v1/agent-governance/agents?${params}`);
}

export async function getAgentProfile(agentId: string): Promise<AgentProfile> {
  return apiFetch(`/api/v1/agent-governance/profile/${agentId}`);
}

export async function registerAgent(data: {
  agent_id: string;
  display_name: string;
  agent_type?: string;
  capabilities?: string[];
}): Promise<AgentProfile> {
  return apiFetch('/api/v1/agent-governance/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getAgentExceptions(agentId?: string, page = 1): Promise<{ items: Record<string, unknown>[]; total: number }> {
  const params = new URLSearchParams({ page: String(page) });
  if (agentId) params.set('agent_id', agentId);
  return apiFetch(`/api/v1/agent-governance/exceptions?${params}`);
}

export async function getAgentNegotiations(agentId?: string, page = 1): Promise<{ items: Record<string, unknown>[]; total: number }> {
  const params = new URLSearchParams({ page: String(page) });
  if (agentId) params.set('agent_id', agentId);
  return apiFetch(`/api/v1/agent-governance/negotiations?${params}`);
}

// ---------------------------------------------------------------------------
// Marketplace (Phase 6c)
// ---------------------------------------------------------------------------

export interface RulePackage {
  id: string;
  name: string;
  version: string;
  publisher_id: string;
  description: string;
  license: string;
  homepage: string | null;
  changelog: unknown[];
  metadata: Record<string, unknown>;
  quality_score: number;
  adoption_count: number;
  published: boolean;
  published_at: string | null;
  rule_count: number;
  created_at: string;
}

export interface PackageList {
  items: RulePackage[];
  total: number;
  page: number;
  page_size: number;
}

export interface PackageSubscription {
  id: string;
  project_id: string;
  package_id: string;
  package_name: string;
  version_constraint: string;
  auto_update: boolean;
  installed_version: string;
  last_synced_at: string;
  created_at: string;
}

export async function getPackages(publishedOnly = false, page = 1, pageSize = 20): Promise<PackageList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (publishedOnly) params.set('published_only', 'true');
  return apiFetch(`/api/v1/marketplace?${params}`);
}

export async function getPackage(id: string): Promise<RulePackage> {
  return apiFetch(`/api/v1/marketplace/${id}`);
}

export async function createPackage(data: {
  name: string;
  version: string;
  description?: string;
  license?: string;
}): Promise<RulePackage> {
  return apiFetch('/api/v1/marketplace', { method: 'POST', body: JSON.stringify(data) });
}

export async function publishPackage(id: string): Promise<RulePackage> {
  return apiFetch(`/api/v1/marketplace/${id}/publish`, { method: 'POST' });
}

export async function subscribeToPackage(projectId: string, packageId: string, versionConstraint = '*'): Promise<PackageSubscription> {
  return apiFetch('/api/v1/marketplace/subscribe', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, package_id: packageId, version_constraint: versionConstraint }),
  });
}

export async function getSubscriptions(projectId?: string): Promise<{ items: PackageSubscription[]; total: number }> {
  const params = new URLSearchParams();
  if (projectId) params.set('project_id', projectId);
  return apiFetch(`/api/v1/marketplace/subscriptions?${params}`);
}

export async function unsubscribe(subscriptionId: string): Promise<void> {
  await apiFetch(`/api/v1/marketplace/subscriptions/${subscriptionId}`, { method: 'DELETE' });
}

// ---------------------------------------------------------------------------
// Activity Review (Two-Tier Compliance)
// ---------------------------------------------------------------------------

export interface RuleRelevanceItem {
  rule_id: string;
  rule_statement: string;
  modality: string;
  severity: string;
  relevance: string;
  relevance_score: number;
  relevance_reason: string;
}

export interface RoughReviewResponse {
  review_id: string;
  total_rules_scanned: number;
  relevant_count: number;
  potentially_relevant_count: number;
  not_relevant_count: number;
  rule_assessments: RuleRelevanceItem[];
  llm_triage_used: boolean;
  latency_ms: number;
}

export interface DetailedReviewResponse {
  review_id: string;
  overall_verdict: string;
  rule_verdicts: Array<{ rule_id: string; rule_statement: string; verdict: string; confidence: number; reasoning: string; issue_description: string; fix_suggestion: string | null }>;
  violations: Array<{ rule_id: string; rule_statement: string; verdict: string; confidence: number; reasoning: string; issue_description: string; fix_suggestion: string | null }>;
  warnings: Array<{ rule_id: string; rule_statement: string; verdict: string; confidence: number; reasoning: string; issue_description: string; fix_suggestion: string | null }>;
  rules_evaluated: number;
  rules_passed: number;
  rules_violated: number;
  rules_uncertain: number;
  fix_summary: string | null;
  total_latency_ms: number;
  chunk_count: number;
}

export interface CombinedReviewResponse {
  rough_review: RoughReviewResponse;
  detailed_review: DetailedReviewResponse;
}

export async function roughReview(data: Record<string, unknown>): Promise<RoughReviewResponse> {
  return apiFetch('/api/v1/evaluate/review/rough', { method: 'POST', body: JSON.stringify(data) });
}

export async function detailedReview(data: Record<string, unknown>): Promise<DetailedReviewResponse> {
  return apiFetch('/api/v1/evaluate/review/detailed', { method: 'POST', body: JSON.stringify(data) });
}

export async function combinedReview(data: Record<string, unknown>): Promise<CombinedReviewResponse> {
  return apiFetch('/api/v1/evaluate/review', { method: 'POST', body: JSON.stringify(data) });
}
