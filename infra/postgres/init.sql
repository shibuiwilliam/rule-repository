-- PostgreSQL initialization script for Rule Repository
-- This runs once when the postgres container is first created.
-- Table creation is handled by Alembic migrations, not this file.
-- Only extensions and non-table setup belong here.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
