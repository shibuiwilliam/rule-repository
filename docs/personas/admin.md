# Admin Persona Guide

## Overview

The Admin persona provides an administrative view of the Rule Repository, focused on system configuration, tenant management, user management, and platform-wide settings.

## Getting Started

1. Navigate to the Admin dashboard at `/admin`
2. Your default view shows the Admin Overview Dashboard
3. Use the sidebar to access tenant management, user management, and system settings

## Key Workflows

### Tenant Management
- View and manage tenants within the platform
- Configure tenant-level settings and feature flags

### User Management
- Manage user accounts, roles, and permissions
- Assign users to organizational units and personas

### System Configuration
- Configure platform-wide settings including feature flags
- Monitor system health and service status

## Vocabulary
- **Rule** = Platform configuration or governance policy
- **Violation** = Configuration or access that does not meet administrative requirements
- **Evaluation** = Administrative review of platform settings or access controls
- **Subject** = System configuration, user account, or tenant setting

## Implementation Status

- **Route group**: `(admin)`
- **Pages**: Dashboard + 2 sub-pages
- **Integration level**: Placeholder (static demo data only)
- **Notable sub-pages**: tenants, users (both use static demonstration data)
