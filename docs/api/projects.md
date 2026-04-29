# Projects API

Rules in the Rule Repository are scoped to **projects**. A project represents a codebase, team, or application that has its own set of rules.

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/projects` | Create a project |
| GET | `/api/v1/projects` | List all projects |
| GET | `/api/v1/projects/{id}` | Get project details |
| PATCH | `/api/v1/projects/{id}` | Update project |
| DELETE | `/api/v1/projects/{id}` | Delete project |

## How Projects Relate to Rules

- Every rule belongs to a project (via `project_id` foreign key)
- The `POST /api/v1/rules` endpoint accepts an optional `project_id` query parameter
- `GET /api/v1/rules?project_id=...` filters rules by project
- The frontend provides a **Project Selector** that scopes the entire UI to one project
- Elasticsearch indexes include `project_id` for filtered search
- A default project is auto-created if none exists

## Example

```bash
# Create a project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Backend API", "description": "Python FastAPI backend"}'

# Create a rule in that project
curl -X POST "http://localhost:8000/api/v1/rules?project_id=<project-id>" \
  -H "Content-Type: application/json" \
  -d '{"statement": "All endpoints must validate input with Pydantic", "modality": "MUST"}'
```
