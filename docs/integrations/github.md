# GitHub PR Review

The Rule Repository can automatically review pull requests on GitHub, posting structured comments when code changes violate rules.

## How It Works

1. A pull request is opened or updated on GitHub.
2. GitHub sends a webhook event to the Rule Repository server.
3. The server fetches the PR diff from the GitHub API.
4. The diff is evaluated against applicable rules (scoped by repository and file paths).
5. A structured review comment is posted on the PR with any violations found.

## Setup

### 1. Configure the Webhook Secret

Add the following to your `.env`:

```
GITHUB_WEBHOOK_SECRET=your-secret-here
GITHUB_TOKEN=ghp_your-token-here
```

The `GITHUB_TOKEN` needs `repo` scope (or `pull_requests: write` for fine-grained tokens) to post review comments.

### 2. Register the Webhook

In your GitHub repository settings, add a webhook:

| Field | Value |
|---|---|
| **Payload URL** | `https://your-server.example.com/api/v1/integrations/webhooks/github` |
| **Content type** | `application/json` |
| **Secret** | Same value as `GITHUB_WEBHOOK_SECRET` |
| **Events** | Select: **Pull requests** |

### 3. Events Handled

| Event | Trigger | Action |
|---|---|---|
| `pull_request.opened` | PR is created | Full diff evaluation |
| `pull_request.synchronize` | New commits pushed to PR | Re-evaluation of updated diff |

Other pull request events are acknowledged but not processed.

## Review Comment Format

When violations are found, the server posts a review comment with this structure:

```markdown
## Rule Repository Review

### Violations

| File | Line | Rule | Issue | Suggested Fix |
|---|---|---|---|---|
| `src/api/auth.py` | 42 | SEC-001 | Missing input validation on user-supplied token | Add `validate_token()` call before processing |
| `src/config.py` | 15 | ENG-003 | Bare `Exception` raised | Use `ConfigError` from the project exception hierarchy |

### Suggestions

- Consider adding type hints to the new `process_request` function (ENG-002).

---
*Evaluated against 12 rules in scope `engineering`.*
```

## Security

Webhook payloads are verified using **HMAC-SHA256** signature validation. The server checks the `X-Hub-Signature-256` header against the configured `GITHUB_WEBHOOK_SECRET`. Requests with missing or invalid signatures are rejected with HTTP 401.

## Current Limitations

- **GitHub Check Run creation is not yet implemented.** The integration posts review comments only. A future update will create Check Runs with inline annotations on the Files Changed tab.

## Troubleshooting

| Issue | Solution |
|---|---|
| No comment appears on PR | Verify the webhook is active in GitHub settings. Check server logs for delivery errors. |
| 401 from webhook endpoint | Ensure `GITHUB_WEBHOOK_SECRET` matches between GitHub and the server `.env`. |
| Comment appears but no violations | The diff may not match any rules in scope. Check that rules exist for the repository scope. |

## See Also

- [CI Pipeline Integration](ci.md) -- using `rulerepo-check` in GitHub Actions
- [Agent Hooks](agent-hooks.md) -- real-time rule checking during agent coding
