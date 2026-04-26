/**
 * Integrations dashboard — GitHub App, CI Pipeline, Agent Hooks configuration.
 * Per CLAUDE_ENHANCE.md §3.7.
 */

const GITHUB_ACTIONS_SNIPPET = `# .github/workflows/rule-check.yml
name: Rule Compliance Check
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v4
      - run: uv tool install rulerepo-cli
      - run: |
          rulerepo-check \\
            --diff "$(git diff origin/main...HEAD)" \\
            --format github-actions \\
            --server-url \${{ secrets.RULEREPO_SERVER_URL }}
`;

const CLAUDE_HOOKS_SNIPPET = `// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "rulerepo-hook preflight --file \\"$TOOL_INPUT_FILE_PATH\\""
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "rulerepo-hook posthoc --file \\"$TOOL_INPUT_FILE_PATH\\""
      }
    ]
  }
}`;

const INGEST_SNIPPET = `# Import your existing CLAUDE.md as rules
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python

# Then review and approve at http://localhost:3000/documents`;

export default function IntegrationsPage() {
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Integrations</h1>
      <p className="text-gray-600">
        Connect the Rule Repository to your development workflow — CI pipelines, PR reviews,
        and coding agents.
      </p>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* GitHub App */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-2 text-lg font-semibold">GitHub PR Review</h2>
          <p className="mb-4 text-sm text-gray-600">
            Automatically evaluate pull requests against organizational rules and post review
            comments with violations and fix suggestions.
          </p>
          <div className="mb-3 rounded bg-gray-50 p-3">
            <p className="mb-1 text-xs font-medium text-gray-500">Webhook URL</p>
            <code className="text-sm">
              {process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}
              /api/v1/integrations/webhooks/github
            </code>
          </div>
          <p className="text-xs text-gray-500">
            Configure this URL in your GitHub repository&apos;s webhook settings. Set content type
            to <code>application/json</code> and select the <code>pull_request</code> event.
          </p>
        </div>

        {/* CI Pipeline */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-2 text-lg font-semibold">CI Pipeline</h2>
          <p className="mb-4 text-sm text-gray-600">
            Add rule compliance checking as a CI step. Blocks PRs that violate MUST rules.
          </p>
          <details className="group">
            <summary className="cursor-pointer text-sm font-medium text-blue-600">
              GitHub Actions configuration
            </summary>
            <pre className="mt-2 overflow-x-auto rounded bg-gray-900 p-3 text-xs text-green-400">
              {GITHUB_ACTIONS_SNIPPET}
            </pre>
          </details>
        </div>

        {/* Agent Hooks */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-2 text-lg font-semibold">Claude Code Hooks</h2>
          <p className="mb-4 text-sm text-gray-600">
            Inject applicable rules before the agent writes code. Evaluate changes after edits.
            Creates a closed feedback loop.
          </p>
          <details className="group">
            <summary className="cursor-pointer text-sm font-medium text-blue-600">
              Hook configuration
            </summary>
            <pre className="mt-2 overflow-x-auto rounded bg-gray-900 p-3 text-xs text-green-400">
              {CLAUDE_HOOKS_SNIPPET}
            </pre>
          </details>
        </div>

        {/* Rule Ingestion */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-2 text-lg font-semibold">Rule Ingestion</h2>
          <p className="mb-4 text-sm text-gray-600">
            Import rules from existing CLAUDE.md files into the repository. Extracted rules go
            through the standard review and approval workflow.
          </p>
          <details className="group">
            <summary className="cursor-pointer text-sm font-medium text-blue-600">
              Ingestion command
            </summary>
            <pre className="mt-2 overflow-x-auto rounded bg-gray-900 p-3 text-xs text-green-400">
              {INGEST_SNIPPET}
            </pre>
          </details>
        </div>
      </div>
    </div>
  );
}
