# Engineering Persona Walkthrough

> Time: ~15 minutes. Prerequisites: `make up && make seed` completed.

## 1. Access the Engineering Portal

Open http://localhost:3000/dashboard in your browser. You are in the Engineering persona by default.

The sidebar shows: Dashboard, Intelligence, Compliance, Feedback, Notifications, Agents, Audit (Observe); Rules, Discover, Documents, Proposals, Snapshots, Departments (Manage); Assistant, Ask, Search, Playground (Use).

## 2. Browse Rules

Navigate to **Rules** in the sidebar. You see the full rule list with modality badges (MUST, MUST_NOT, SHOULD) and severity indicators (LOW through CRITICAL).

Filter by scope `engineering/python` to see Python-specific rules. Notice the structured scope dimensions in each rule's detail view.

## 3. Search for Rules

Navigate to **Search**. Type `"API endpoint must validate input"` — the hybrid search returns relevant rules ranked by BM25 + semantic similarity.

Try a category search: filter by `modality=MUST`, `severity=HIGH`.

## 4. Evaluate Code Compliance

Navigate to **Playground**. Paste a sample Python diff:

```diff
--- a/api/handler.py
+++ b/api/handler.py
@@ -10,6 +10,9 @@ async def create_user(request):
+    name = request.json["name"]
+    email = request.json["email"]
+    db.execute(f"INSERT INTO users (name, email) VALUES ('{name}', '{email}')")
```

Click **Evaluate**. The system identifies SQL injection risk (string interpolation in query) and returns a DENY verdict with a `code_edit` remediation suggesting parameterized queries.

## 5. Discover Rules from Code

Navigate to **Discover**. Upload a `ruff.toml` or `.eslintrc.json` file. The discovery engine identifies implicit rules from linter configurations and proposes them as rule candidates.

Review candidates and approve the ones that should become formal rules.

## 6. Use the CLI

In your terminal:

```bash
# Evaluate a diff
rulerepo-check --diff "$(git diff HEAD~1)" --format text

# Inject rules before editing
rulerepo-hook preflight --file src/api/handler.py
```

## 7. Switch Personas

Click the **persona switcher** dropdown (top of sidebar). Select **Legal**, **HR**, or **Finance** to see their domain-specific dashboards with different KPIs, rule scopes, and navigation items.

## Verification

- [ ] Dashboard loads with compliance rate and violation trends
- [ ] Rules list shows engineering rules
- [ ] Search returns relevant results
- [ ] Playground evaluation produces a verdict
- [ ] Persona switcher navigates to other portals
