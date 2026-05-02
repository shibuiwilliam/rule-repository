"""Tests for the rule marketplace schemas and serialization."""

from __future__ import annotations

from rulerepo_server.schemas.marketplace import (
    ConflictResolveRequest,
    PackageCreate,
    PackageRuleAdd,
    SubscribeRequest,
)


class TestPackageSchemas:
    def test_package_create_minimal(self) -> None:
        p = PackageCreate(name="owasp-top-10", version="1.0.0")
        assert p.name == "owasp-top-10"
        assert p.version == "1.0.0"
        assert p.license == "MIT"
        assert p.description == ""

    def test_package_create_full(self) -> None:
        p = PackageCreate(
            name="security-rules",
            version="2.1.0",
            description="OWASP security rules",
            license="Apache-2.0",
            homepage="https://example.com",
            metadata={"certifications": ["soc2"]},
        )
        assert p.license == "Apache-2.0"
        assert p.metadata["certifications"] == ["soc2"]

    def test_package_rule_add(self) -> None:
        r = PackageRuleAdd(rule_id="rule-123", package_rule_id="owasp-a01")
        assert r.package_rule_id == "owasp-a01"

    def test_subscribe_request(self) -> None:
        s = SubscribeRequest(
            project_id="proj-1",
            package_id="pkg-1",
            version_constraint="^2.0.0",
        )
        assert s.version_constraint == "^2.0.0"
        assert s.auto_update is False

    def test_subscribe_request_defaults(self) -> None:
        s = SubscribeRequest(project_id="proj-1", package_id="pkg-1")
        assert s.version_constraint == "*"

    def test_conflict_resolve_request(self) -> None:
        r = ConflictResolveRequest(resolution="prefer_a")
        assert r.resolved_by == "system"

    def test_conflict_resolve_with_user(self) -> None:
        r = ConflictResolveRequest(resolution="prefer_b", resolved_by="alice")
        assert r.resolved_by == "alice"


class TestSerializationHelpers:
    def test_package_to_dict(self) -> None:
        from unittest.mock import MagicMock

        from rulerepo_server.services.marketplace.service import _package_to_dict

        pkg = MagicMock()
        pkg.id = "pkg-1"
        pkg.name = "test-package"
        pkg.version = "1.0.0"
        pkg.publisher_id = "publisher-1"
        pkg.description = "Test"
        pkg.license = "MIT"
        pkg.homepage = None
        pkg.changelog = []
        pkg.metadata_ = {}
        pkg.quality_score = 0.85
        pkg.adoption_count = 42
        pkg.published = True
        pkg.published_at = None
        pkg.created_at = None

        d = _package_to_dict(pkg)
        assert d["name"] == "test-package"
        assert d["version"] == "1.0.0"
        assert d["adoption_count"] == 42
        assert d["published"] is True
        assert d["published_at"] is None
        assert d["created_at"] == ""

    def test_subscription_to_dict(self) -> None:
        from unittest.mock import MagicMock

        from rulerepo_server.services.marketplace.service import _subscription_to_dict

        sub = MagicMock()
        sub.id = "sub-1"
        sub.project_id = "proj-1"
        sub.package_id = "pkg-1"
        sub.version_constraint = "^2.0.0"
        sub.auto_update = True
        sub.composition_policy = {}
        sub.installed_version = "2.1.0"
        sub.last_synced_at = None
        sub.created_at = None

        d = _subscription_to_dict(sub)
        assert d["auto_update"] is True
        assert d["version_constraint"] == "^2.0.0"
        assert d["installed_version"] == "2.1.0"
        assert d["composition_policy"] == {}
        assert d["last_synced_at"] == ""
        assert d["created_at"] == ""
