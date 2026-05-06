#!/usr/bin/env python3
"""Verify the integrity of the audit log hash chain.

Connects to PostgreSQL, reads the audit_log table ordered by timestamp,
and verifies that each entry's previous_hash matches the entry_hash of
the preceding entry. Reports any chain breaks.

Usage:
    uv run python scripts/verify_audit_chain.py
    uv run python scripts/verify_audit_chain.py --since 7d
    uv run python scripts/verify_audit_chain.py --limit 5000
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta

# Add the server source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "server", "src"))

# Well-known genesis hash (must match domain/audit.py)
GENESIS_HASH = "0" * 64


def compute_hash(previous_hash: str, entry_data: dict) -> str:
    """Recompute the SHA-256 hash for an audit entry."""
    canonical = json.dumps(entry_data, sort_keys=True, default=str)
    payload = f"{previous_hash}{canonical}"
    return hashlib.sha256(payload.encode()).hexdigest()


def parse_since(value: str) -> datetime:
    """Parse a relative duration like '7d', '24h', '30m' into a datetime."""
    unit = value[-1].lower()
    amount = int(value[:-1])
    now = datetime.now(tz=UTC)
    if unit == "d":
        return now - timedelta(days=amount)
    if unit == "h":
        return now - timedelta(hours=amount)
    if unit == "m":
        return now - timedelta(minutes=amount)
    msg = f"Unknown duration unit '{unit}'. Use 'd' (days), 'h' (hours), or 'm' (minutes)."
    raise ValueError(msg)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Verify audit log hash chain integrity")
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only verify entries newer than this duration (e.g. 7d, 24h, 30m)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of entries to verify (0 = unlimited)",
    )
    args = parser.parse_args()

    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from rulerepo_server.adapters.postgres.models import AuditLogModel

    database_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://rule:rule@localhost:5432/ruledb")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    print("Audit Log Chain Verification")
    print("=" * 60)

    async with session_factory() as session:
        # Get total count
        count_result = await session.execute(select(func.count(AuditLogModel.id)))
        total_entries = count_result.scalar_one()
        print(f"Total audit log entries: {total_entries}")

        if total_entries == 0:
            print("No entries to verify. Chain is trivially valid.")
            await engine.dispose()
            return

        # Build query
        query = select(AuditLogModel).order_by(AuditLogModel.timestamp.asc())

        since_dt = None
        if args.since:
            since_dt = parse_since(args.since)
            print(f"Filtering entries since: {since_dt.isoformat()}")

        if since_dt:
            # When filtering by time, we need the entry just before the window
            # to verify the chain continues correctly
            query = query.where(AuditLogModel.timestamp >= since_dt)

        if args.limit > 0:
            query = query.limit(args.limit)

        result = await session.execute(query)
        entries = list(result.scalars().all())

        print(f"Entries to verify: {len(entries)}")
        print("-" * 60)

        if not entries:
            print("No entries in the specified range.")
            await engine.dispose()
            return

        breaks_found: list[dict] = []
        entries_checked = 0
        missing_fields: list[dict] = []

        # Determine the expected previous_hash for the first entry
        if since_dt:
            # Get the entry just before our window to chain from
            pre_query = (
                select(AuditLogModel.entry_hash)
                .where(AuditLogModel.timestamp < since_dt)
                .order_by(AuditLogModel.timestamp.desc())
                .limit(1)
            )
            pre_result = await session.execute(pre_query)
            pre_hash = pre_result.scalar_one_or_none()
            expected_previous = pre_hash if pre_hash else GENESIS_HASH
        else:
            expected_previous = GENESIS_HASH

        for entry in entries:
            entries_checked += 1

            # Check required fields
            missing = []
            if not entry.action:
                missing.append("action")
            if not entry.actor:
                missing.append("actor")
            if not entry.resource_type:
                missing.append("resource_type")
            if not entry.resource_id:
                missing.append("resource_id")
            if not entry.entry_hash:
                missing.append("entry_hash")
            if not entry.previous_hash:
                missing.append("previous_hash")
            if entry.timestamp is None:
                missing.append("timestamp")

            if missing:
                missing_fields.append(
                    {
                        "entry_id": str(entry.id),
                        "missing": missing,
                    }
                )

            # Verify chain link
            if entry.previous_hash != expected_previous:
                breaks_found.append(
                    {
                        "entry_id": str(entry.id),
                        "timestamp": entry.timestamp.isoformat() if entry.timestamp else "N/A",
                        "action": entry.action,
                        "type": "previous_hash_mismatch",
                        "expected": expected_previous[:16] + "...",
                        "actual": entry.previous_hash[:16] + "...",
                    }
                )

            # Verify entry hash
            entry_data = {
                "id": str(entry.id),
                "action": entry.action,
                "actor": entry.actor,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "details": entry.details,
            }
            computed_hash = compute_hash(entry.previous_hash, entry_data)
            if computed_hash != entry.entry_hash:
                breaks_found.append(
                    {
                        "entry_id": str(entry.id),
                        "timestamp": entry.timestamp.isoformat() if entry.timestamp else "N/A",
                        "action": entry.action,
                        "type": "entry_hash_mismatch",
                        "computed": computed_hash[:16] + "...",
                        "stored": entry.entry_hash[:16] + "...",
                    }
                )

            expected_previous = entry.entry_hash

    await engine.dispose()

    # Report results
    print(f"\nEntries checked: {entries_checked}")

    if missing_fields:
        print(f"\nEntries with missing required fields: {len(missing_fields)}")
        for mf in missing_fields[:10]:
            print(f"  Entry {mf['entry_id']}: missing {', '.join(mf['missing'])}")
        if len(missing_fields) > 10:
            print(f"  ... and {len(missing_fields) - 10} more")

    if breaks_found:
        print(f"\nCHAIN INTEGRITY FAILURES: {len(breaks_found)}")
        for brk in breaks_found[:20]:
            print(f"  [{brk['type']}] Entry {brk['entry_id']} at {brk['timestamp']}")
            if brk["type"] == "previous_hash_mismatch":
                print(f"    Expected previous: {brk['expected']}")
                print(f"    Actual previous:   {brk['actual']}")
            else:
                print(f"    Computed hash: {brk['computed']}")
                print(f"    Stored hash:   {brk['stored']}")
        if len(breaks_found) > 20:
            print(f"  ... and {len(breaks_found) - 20} more failures")
        print("\nResult: FAIL")
        sys.exit(1)
    else:
        print("\nChain integrity: OK")
        print("Result: PASS")


if __name__ == "__main__":
    asyncio.run(main())
