# Admin Persona Walkthrough

> Time: ~10 minutes. Prerequisites: `make up && make seed` completed.

## 1. Access the Admin Portal

Navigate to `http://localhost:3000/admin`. The Admin shell shows a steel-colored sidebar with five navigation items: Dashboard, Tenants, Users, Settings, and Billing.

## 2. Dashboard Overview

The admin dashboard provides system-wide operational metrics:

- **Total rules** across all tenants and projects
- **Active users** and registered agents
- **System health** status (Postgres, Elasticsearch, Neo4j, Redis)
- **LLM cost tracking** and usage trends

## 3. Manage Tenants

Navigate to `/admin/tenants`. In multi-tenant deployments, manage tenant configurations including:

- Tenant creation and deactivation
- Per-tenant feature flag overrides
- LLM provider and budget configuration
- Data residency and regional routing settings

## 4. Manage Users

Navigate to `/admin/users`. Manage user accounts and access:

- SCIM 2.0 integration for identity provisioning
- Department membership and capacity assignments
- Classification clearance levels
- API key management

## Next Steps

- Review [Multi-Tenancy](../architecture/overview.md#tier-1-infrastructure-postgres-only) for deployment tier options
- See [Feature Flags](../../FEATURES.md) for the full configuration reference
- Explore [Docker Compose Setup](../getting-started/docker-compose.md) for infrastructure management
