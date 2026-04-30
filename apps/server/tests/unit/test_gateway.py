"""Unit tests for gateway normalizers and policy matching."""

from rulerepo_server.gateway.normalizers.generic import GenericNormalizer
from rulerepo_server.gateway.normalizers.github import GitHubNormalizer
from rulerepo_server.gateway.normalizers.slack import SlackNormalizer
from rulerepo_server.gateway.policy_engine import match_policies


class TestGitHubNormalizer:
    def test_pull_request_event(self) -> None:
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Add login feature",
                "body": "Implements OAuth2 login",
                "user": {"login": "developer1"},
                "base": {"ref": "main"},
                "head": {"ref": "feat/login"},
                "changed_files": 5,
            },
            "repository": {"full_name": "org/repo"},
        }
        event = GitHubNormalizer().normalize(payload)
        assert event.source == "github"
        assert event.event_type == "pull_request.opened"
        assert event.actor == "developer1"
        assert "PR #42" in event.subject
        assert event.metadata["pr_number"] == 42

    def test_issue_event(self) -> None:
        payload = {
            "action": "created",
            "issue": {
                "number": 10,
                "title": "Bug report",
                "body": "Something is broken",
                "user": {"login": "reporter"},
            },
            "repository": {"full_name": "org/repo"},
        }
        event = GitHubNormalizer().normalize(payload)
        assert event.event_type == "issues.created"
        assert "Issue #10" in event.subject


class TestSlackNormalizer:
    def test_message_event(self) -> None:
        payload = {
            "event": {
                "type": "message",
                "text": "Can we deploy to production?",
                "user": "U12345",
                "channel": "C67890",
            },
            "team_id": "T11111",
        }
        event = SlackNormalizer().normalize(payload)
        assert event.source == "slack"
        assert event.event_type == "message"
        assert event.actor == "U12345"
        assert "production" in event.subject


class TestGenericNormalizer:
    def test_basic_payload(self) -> None:
        payload = {
            "event_type": "deployment.started",
            "actor": "ci-bot",
            "subject": "Deploying v2.1.0",
            "metadata": {"environment": "staging"},
        }
        event = GenericNormalizer().normalize(payload)
        assert event.source == "generic"
        assert event.event_type == "deployment.started"
        assert event.actor == "ci-bot"

    def test_empty_payload(self) -> None:
        event = GenericNormalizer().normalize({})
        assert event.source == "generic"
        assert event.event_type == "generic"


class TestPolicyEngine:
    def test_exact_match(self) -> None:
        from rulerepo_server.gateway.schemas import NormalizedEvent

        event = NormalizedEvent(source="github", event_type="pull_request.opened", subject="test")
        policies = [
            {
                "event_source": "github",
                "event_type_pattern": "pull_request.opened",
                "enabled": True,
            },
            {"event_source": "slack", "event_type_pattern": "*", "enabled": True},
        ]
        matched = match_policies(event, policies)
        assert len(matched) == 1
        assert matched[0]["event_source"] == "github"

    def test_wildcard_match(self) -> None:
        from rulerepo_server.gateway.schemas import NormalizedEvent

        event = NormalizedEvent(source="github", event_type="pull_request.synchronize", subject="test")
        policies = [
            {"event_source": "github", "event_type_pattern": "pull_request.*", "enabled": True},
        ]
        matched = match_policies(event, policies)
        assert len(matched) == 1

    def test_disabled_policy_excluded(self) -> None:
        from rulerepo_server.gateway.schemas import NormalizedEvent

        event = NormalizedEvent(source="github", event_type="push", subject="test")
        policies = [
            {"event_source": "github", "event_type_pattern": "*", "enabled": False},
        ]
        matched = match_policies(event, policies)
        assert len(matched) == 0

    def test_wrong_source_excluded(self) -> None:
        from rulerepo_server.gateway.schemas import NormalizedEvent

        event = NormalizedEvent(source="slack", event_type="message", subject="test")
        policies = [
            {"event_source": "github", "event_type_pattern": "*", "enabled": True},
        ]
        matched = match_policies(event, policies)
        assert len(matched) == 0
