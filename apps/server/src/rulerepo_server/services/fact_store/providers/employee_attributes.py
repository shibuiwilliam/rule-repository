"""Employee attributes fact provider.

Resolves HR-related facts such as employee grade, department, tenure,
employment type, manager, and 36-agreement status.

In development mode the provider returns mock data from a configurable
dictionary.  In production the implementation would query a HRIS sync
table (Workday, SmartHR, etc.) via ``adapters/hr_systems/``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.fact import Fact, FactSchema, FactStatus

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Mock employee data for development
# ---------------------------------------------------------------------------

_MOCK_EMPLOYEES: dict[str, dict[str, Any]] = {
    "E001": {
        "employee_grade": "M2",
        "employee_department": "engineering",
        "employee_tenure_years": 5,
        "employment_type": "full_time",
        "manager_id": "E000",
        "36_agreement_status": "opted_in",
    },
    "E002": {
        "employee_grade": "S1",
        "employee_department": "sales",
        "employee_tenure_years": 2,
        "employment_type": "contract",
        "manager_id": "E001",
        "36_agreement_status": "opted_out",
    },
    "E003": {
        "employee_grade": "L1",
        "employee_department": "legal",
        "employee_tenure_years": 8,
        "employment_type": "full_time",
        "manager_id": "E000",
        "36_agreement_status": "opted_in",
    },
}

# ---------------------------------------------------------------------------
# Supported fact schemas
# ---------------------------------------------------------------------------

_SCHEMAS: list[FactSchema] = [
    FactSchema(
        key="employee_grade",
        description="Employee's grade/level within the company grading system.",
        value_type="str",
        required_context_keys=["employee_id"],
        domain="hr",
    ),
    FactSchema(
        key="employee_department",
        description="Department the employee belongs to.",
        value_type="str",
        required_context_keys=["employee_id"],
        domain="hr",
    ),
    FactSchema(
        key="employee_tenure_years",
        description="Number of full years the employee has been with the company.",
        value_type="int",
        required_context_keys=["employee_id"],
        domain="hr",
    ),
    FactSchema(
        key="employment_type",
        description="Employment type: full_time, part_time, contract, intern.",
        value_type="str",
        required_context_keys=["employee_id"],
        domain="hr",
    ),
    FactSchema(
        key="manager_id",
        description="Employee ID of the direct manager.",
        value_type="str",
        required_context_keys=["employee_id"],
        domain="hr",
    ),
    FactSchema(
        key="36_agreement_status",
        description=(
            "Status of the employee's 36-agreement (saburoku kyoutei) "
            "opt-in under Japanese labor law.  Values: opted_in, opted_out, not_applicable."
        ),
        value_type="str",
        required_context_keys=["employee_id"],
        domain="hr",
    ),
]


class EmployeeAttributesProvider:
    """Resolves employee attribute facts from HR master data.

    Attributes:
        name: Provider name.
        domain: Business domain.
    """

    name: str = "employee_attributes"
    domain: str = "hr"

    def __init__(
        self,
        mock_data: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._data = mock_data if mock_data is not None else _MOCK_EMPLOYEES

    async def supported_facts(self) -> list[FactSchema]:
        """Return the list of employee-related fact schemas."""
        return list(_SCHEMAS)

    async def fetch(self, key: str, context: dict[str, Any]) -> Fact | None:
        """Resolve an employee attribute fact.

        Args:
            key: Fact key (e.g., ``employee_grade``).
            context: Must contain ``employee_id``.

        Returns:
            Resolved ``Fact`` or ``None`` if the employee or attribute
            is not found.
        """
        employee_id = context.get("employee_id")
        if not employee_id:
            logger.warning("employee_attributes_missing_context", key=key)
            return None

        employee = self._data.get(employee_id)
        if employee is None:
            return None

        value = employee.get(key)
        if value is None:
            return None

        return Fact(
            key=key,
            value=value,
            status=FactStatus.RESOLVED,
            source_provider=self.name,
            resolved_at=datetime.now(tz=UTC),
            ttl_seconds=3600,  # 1 hour cache for employee data
            metadata={"employee_id": employee_id},
        )

    async def health_check(self) -> bool:
        """Employee attributes provider is always healthy in dev mode."""
        return True
