"""IT Security context assembler — transforms IaC plans and access requests into LLM-ready text."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class ITSecurityContextAssembler:
    """Assembles LLM-ready context from IT Security artifacts.

    Handles:
    - iac_plan: Terraform / CloudFormation plan output with resources,
      changes, security groups, and IAM policies.
    - access_request: user, resource, access level, justification,
      duration, and approver information.
    """

    async def assemble(self, evaluable: dict[str, Any]) -> str:
        """Transform an IT Security evaluable into structured context text."""
        artifact_type = evaluable.get("artifact_type", "iac_plan")
        payload = evaluable.get("payload", {})
        metadata = evaluable.get("metadata", {})

        parts: list[str] = []

        # Common metadata
        if environment := metadata.get("environment"):
            parts.append(f"Environment: {environment}")
        if cloud_provider := metadata.get("cloud_provider"):
            parts.append(f"Cloud Provider: {cloud_provider}")
        if project := metadata.get("project"):
            parts.append(f"Project: {project}")
        if compliance_framework := metadata.get("compliance_framework"):
            parts.append(f"Compliance Framework: {compliance_framework}")

        if artifact_type == "iac_plan":
            parts.extend(self._assemble_iac_plan(payload))
        elif artifact_type == "access_request":
            parts.extend(self._assemble_access_request(payload))
        else:
            parts.append(str(payload))

        context = "\n".join(parts)
        logger.debug(
            "it_security_context_assembled",
            artifact_type=artifact_type,
            length=len(context),
        )
        return context

    def _assemble_iac_plan(self, payload: dict[str, Any]) -> list[str]:
        """Build context sections for an IaC plan artifact."""
        parts: list[str] = []

        if plan_format := payload.get("plan_format"):
            parts.append(f"Plan Format: {plan_format}")

        if plan_output := payload.get("plan_output"):
            parts.append(f"\n--- IAC PLAN OUTPUT ---\n{plan_output}")

        if resources := payload.get("resources"):
            parts.append("\n--- RESOURCES ---")
            for resource in resources:
                resource_type = resource.get("type", "unknown")
                resource_name = resource.get("name", "unnamed")
                action = resource.get("action", "unknown")
                parts.append(f"  [{action}] {resource_type}: {resource_name}")
                if properties := resource.get("properties"):
                    for key, value in properties.items():
                        parts.append(f"    {key}: {value}")

        if security_groups := payload.get("security_groups"):
            parts.append("\n--- SECURITY GROUPS ---")
            for sg in security_groups:
                sg_name = sg.get("name", "unnamed")
                parts.append(f"  Security Group: {sg_name}")
                for rule in sg.get("ingress_rules", []):
                    parts.append(
                        f"    INGRESS: {rule.get('cidr', 'N/A')} -> "
                        f"port {rule.get('port', 'N/A')} ({rule.get('protocol', 'N/A')})"
                    )
                for rule in sg.get("egress_rules", []):
                    parts.append(
                        f"    EGRESS: port {rule.get('port', 'N/A')} -> "
                        f"{rule.get('cidr', 'N/A')} ({rule.get('protocol', 'N/A')})"
                    )

        if iam_policies := payload.get("iam_policies"):
            parts.append("\n--- IAM POLICIES ---")
            for policy in iam_policies:
                policy_name = policy.get("name", "unnamed")
                parts.append(f"  Policy: {policy_name}")
                for stmt in policy.get("statements", []):
                    effect = stmt.get("effect", "unknown")
                    actions = stmt.get("actions", [])
                    resources = stmt.get("resources", [])
                    actions_str = ", ".join(actions) if isinstance(actions, list) else str(actions)
                    resources_str = ", ".join(resources) if isinstance(resources, list) else str(resources)
                    parts.append(f"    {effect}: actions=[{actions_str}] resources=[{resources_str}]")

        if tags := payload.get("tags"):
            parts.append("\n--- RESOURCE TAGS ---")
            for key, value in tags.items():
                parts.append(f"  {key}: {value}")

        if encryption := payload.get("encryption"):
            parts.append(f"\n--- ENCRYPTION ---\n{encryption}")

        return parts

    def _assemble_access_request(self, payload: dict[str, Any]) -> list[str]:
        """Build context sections for an access request artifact."""
        parts: list[str] = []

        if requester := payload.get("requester"):
            parts.append(f"Requester: {requester}")
        if requester_role := payload.get("requester_role"):
            parts.append(f"Requester Role: {requester_role}")
        if resource := payload.get("resource"):
            parts.append(f"Resource: {resource}")
        if access_level := payload.get("access_level"):
            parts.append(f"Access Level: {access_level}")
        if justification := payload.get("justification"):
            parts.append(f"Justification: {justification}")
        if duration := payload.get("duration"):
            parts.append(f"Duration: {duration}")
        if approver := payload.get("approver"):
            parts.append(f"Approver: {approver}")
        if mfa_enabled := payload.get("mfa_enabled"):
            parts.append(f"MFA Enabled: {mfa_enabled}")
        elif "mfa_enabled" in payload:
            parts.append(f"MFA Enabled: {payload['mfa_enabled']}")
        if approval_chain := payload.get("approval_chain"):
            chain_str = " -> ".join(approval_chain) if isinstance(approval_chain, list) else str(approval_chain)
            parts.append(f"Approval Chain: {chain_str}")
        if risk_score := payload.get("risk_score"):
            parts.append(f"Risk Score: {risk_score}")

        return parts
