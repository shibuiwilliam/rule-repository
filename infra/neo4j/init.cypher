// Neo4j initialization constraints for Rule Repository
CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.id IS UNIQUE;
CREATE INDEX rule_modality IF NOT EXISTS FOR (r:Rule) ON (r.modality);
CREATE INDEX rule_severity IF NOT EXISTS FOR (r:Rule) ON (r.severity);
CREATE INDEX rule_status IF NOT EXISTS FOR (r:Rule) ON (r.status);
