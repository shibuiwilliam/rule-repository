-- PostgreSQL initialization script for Rule Repository
-- This runs once when the postgres container is first created.
-- Table creation is handled by Alembic migrations, not this file.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Adjacency table for rule relationships (Tier 1/2 graph fallback).
-- In Tier 3 deployments Neo4j is the primary graph store, but this
-- table is always populated as a Postgres-authoritative projection.
CREATE TABLE IF NOT EXISTS rule_relationships (
    source_id   UUID         NOT NULL,
    target_id   UUID         NOT NULL,
    rel_type    VARCHAR(50)  NOT NULL,
    basis_type  VARCHAR(100),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (source_id, target_id, rel_type)
);

CREATE INDEX IF NOT EXISTS idx_rule_relationships_source
    ON rule_relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rule_relationships_target
    ON rule_relationships(target_id);
