-- ============================================================================
-- BRONZE — ingest raw JSON from the landing volume via Auto Loader (read_files)
-- Volume -> Bronze streaming tables. Faithful, replayable, +ingestion metadata.
-- ============================================================================

CREATE OR REFRESH STREAMING TABLE bronze_customer_profiles AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/<CATALOG>/telcoabc_retention/landing/customer_profiles',
  format => 'json', schemaEvolutionMode => 'addNewColumns');

CREATE OR REFRESH STREAMING TABLE bronze_call_interactions AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/<CATALOG>/telcoabc_retention/landing/call_interactions',
  format => 'json', schemaEvolutionMode => 'addNewColumns');

CREATE OR REFRESH STREAMING TABLE bronze_agents AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/<CATALOG>/telcoabc_retention/landing/agents',
  format => 'json', schemaEvolutionMode => 'addNewColumns');

CREATE OR REFRESH STREAMING TABLE bronze_service_events AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/<CATALOG>/telcoabc_retention/landing/service_events',
  format => 'json', schemaEvolutionMode => 'addNewColumns');

CREATE OR REFRESH STREAMING TABLE bronze_competitor_intel AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/<CATALOG>/telcoabc_retention/landing/competitor_intel',
  format => 'json', schemaEvolutionMode => 'addNewColumns');

CREATE OR REFRESH STREAMING TABLE bronze_retention_offers AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/<CATALOG>/telcoabc_retention/landing/retention_offers',
  format => 'json', schemaEvolutionMode => 'addNewColumns');
