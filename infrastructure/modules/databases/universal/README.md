# Universal Multi-Cloud Distributed Database Module

This module provisions a **Universal Multi-Cloud Distributed SQL Database** (CockroachDB / YugabyteDB) that runs across AWS (EKS), Azure (AKS), and GCP (GKE).

## Architecture & Capabilities

- **Cloud-Agnostic Active-Active Consensus**: Built on Raft consensus algorithm spanning nodes across AWS, Azure, and GCP.
- **Resilience to Cloud Outages**: If an entire cloud provider (e.g., AWS or Azure) experiences downtime, the database automatically maintains quorum and continues serving queries without data loss.
- **High-Throughput Request Handling**: Designed for heavy API traffic, inference request logging, patient records, and real-time feature store queries.
- **Wire-Compatible with PostgreSQL**: Uses standard PostgreSQL wire protocol (Port 26257 / 5432) for compatibility with SQLAlchemy, Psycopg2, and FastAPI application stacks.
- **Zero-Trust Encryption**: Enforces TLS 1.3 in-transit encryption and AES-256 at-rest storage encryption.

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `enable_universal_database` | Feature flag to enable universal database | `true` |
| `nodes_per_cloud` | Number of database nodes per cloud provider | `3` |
| `storage_gb_per_node` | Persistent Volume size per node (GB) | `100` |
| `database_name` | Primary clinical trial database name | `mlops_clinical_trials_universal` |
| `enable_encryption` | Enable TLS and at-rest encryption | `true` |
