# Engineering Persona Guide

## Overview

The Engineering persona provides a code-centric view of the Rule Repository, focused on maintaining coding standards, security practices, and documentation conventions.

## Getting Started

1. Navigate to the Engineering dashboard at `/dashboard`
2. Your default view shows the Code Compliance Dashboard
3. Use the sidebar to access rules, playground, discovery, and intelligence

## Key Workflows

### Running a Compliance Check
- Submit code changes via `POST /api/v1/submissions` with `kind: "code_change"`
- Or use the CLI: `rulerepo-check --diff "$(git diff)" --format github-actions`
- Or use agent hooks: `rulerepo-hook preflight --file src/api/handler.py`

### Discovering Rules from Existing Code
- Navigate to Discovery to scan CLAUDE.md files, linter configs, and code patterns
- Review discovered rule candidates and approve or dismiss them

### Using the Playground
- Test rules against sample code changes
- The playground defaults to code editor mode for the Engineering persona

### MCP Integration
- Connect your AI coding agent via the MCP server
- Tools: `search_rules`, `evaluate_compliance`, `get_rules_for_context`

## Vocabulary
- **Rule** = Coding standard or engineering guideline
- **Violation** = Code that doesn't meet a rule
- **Evaluation** = Code review against rules
- **Subject** = Code change (diff or file set)

## Templates
- `python-fastapi` -- Python/FastAPI coding standards
- `typescript-react` -- TypeScript/React component standards
- `security-owasp` -- OWASP security checklist
- `api-design` -- API design conventions
- `testing-standards` -- Test coverage and quality

## Implementation Status

- **Route group**: `(dashboard)`
- **Pages**: Full dashboard with all sub-pages functional
- **Integration level**: Fully API-integrated
- **Notable sub-pages**: Code compliance dashboard, rules listing, playground, discovery, intelligence
