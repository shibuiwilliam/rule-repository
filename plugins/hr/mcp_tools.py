"""HR-specific MCP tool definitions for the HR plugin.

Each tool is defined as a dict with ``name``, ``description``, and
``input_schema`` (JSON Schema).  The MCP server registers these tools
at startup when the HR plugin is enabled.

See: CLAUDE.md §14.5 (MCP Clearance), §12.3
"""

from __future__ import annotations

from typing import Any

HR_MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "check_overtime_compliance",
        "description": (
            "Check an employee's overtime compliance for a given month against "
            "Japanese labor law thresholds (36-agreement general limit 45h/month, "
            "special clause absolute cap 100h, health guidance threshold 40h). "
            "Returns compliance status, violations, and 36-agreement status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Unique employee identifier.",
                },
                "month": {
                    "type": "string",
                    "description": "Month to check in YYYY-MM format.",
                    "pattern": r"^\d{4}-\d{2}$",
                },
                "tenant_id": {
                    "type": "string",
                    "description": "Tenant identifier. Defaults to 'default'.",
                    "default": "default",
                },
            },
            "required": ["employee_id", "month"],
        },
    },
    {
        "name": "get_leave_balance",
        "description": (
            "Retrieve an employee's current leave balance, including annual "
            "leave entitlement, days taken, days remaining, carry-over days, "
            "and special leave balances (sick, bereavement, childcare, etc.)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Unique employee identifier.",
                },
            },
            "required": ["employee_id"],
        },
    },
    {
        "name": "evaluate_hr_event",
        "description": (
            "Evaluate an HR event against the rule repository. Supports event "
            "types including overtime_record, leave_request, attendance_anomaly, "
            "contract_renewal, health_check_due, and termination_request. "
            "Uses the event subject adapter for subject-aware evaluation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "Type of HR event (e.g., 'overtime_record', 'leave_request').",
                    "enum": [
                        "overtime_record",
                        "leave_request",
                        "attendance_anomaly",
                        "contract_renewal",
                        "health_check_due",
                        "termination_request",
                        "compensation_change",
                        "harassment_report",
                        "safety_incident",
                        "remote_work_request",
                    ],
                },
                "employee_id": {
                    "type": "string",
                    "description": "Employee involved in the event.",
                },
                "payload": {
                    "type": "object",
                    "description": "Event-specific data. Contents vary by event_type.",
                    "additionalProperties": True,
                },
                "evaluation_mode": {
                    "type": "string",
                    "description": "Evaluation mode: 'single' (event alone), 'sequence' (with monthly window), 'calendar' (annual context).",
                    "enum": ["single", "sequence", "calendar"],
                    "default": "single",
                },
                "jurisdiction": {
                    "type": "string",
                    "description": "Legal jurisdiction (ISO country code). Defaults to 'JP'.",
                    "default": "JP",
                },
            },
            "required": ["event_type", "employee_id"],
        },
    },
    {
        "name": "get_department_compliance",
        "description": (
            "Retrieve a compliance summary for all employees in a department "
            "for a given month. Includes violation count, at-risk employees, "
            "and average overtime hours."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "department_id": {
                    "type": "string",
                    "description": "Department identifier (e.g., 'engineering', 'sales').",
                },
                "month": {
                    "type": "string",
                    "description": "Month to summarize in YYYY-MM format.",
                    "pattern": r"^\d{4}-\d{2}$",
                },
                "tenant_id": {
                    "type": "string",
                    "description": "Tenant identifier. Defaults to 'default'.",
                    "default": "default",
                },
            },
            "required": ["department_id", "month"],
        },
    },
    {
        "name": "search_hr_rules",
        "description": (
            "Search for HR-specific rules in the rule repository. Supports "
            "filtering by category (overtime, leave, employment, safety, etc.), "
            "jurisdiction, severity, and free-text query. Returns matching "
            "rules with their statements, modality, and severity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text search query.",
                },
                "category": {
                    "type": "string",
                    "description": "HR rule category to filter by.",
                    "enum": [
                        "overtime",
                        "leave",
                        "employment",
                        "safety",
                        "compensation",
                        "harassment",
                        "termination",
                        "remote_work",
                        "maternity",
                        "work_hours",
                    ],
                },
                "jurisdiction": {
                    "type": "string",
                    "description": "Filter by jurisdiction (ISO country code).",
                    "default": "JP",
                },
                "severity": {
                    "type": "string",
                    "description": "Minimum severity level.",
                    "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": [],
        },
    },
]
