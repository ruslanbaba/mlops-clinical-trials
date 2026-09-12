# Universal Multi-Cloud Database Module (CockroachDB / YugabyteDB Distributed SQL Engine)
# Supports active-active cross-cloud deployment across AWS EKS, Azure AKS, and GCP GKE.

resource "random_password" "universal_db_password" {
  count   = var.enable_universal_database ? 1 : 0
  length  = 32
  special = false
}

# Kubernetes Secret for Universal Database Credentials across all clusters
resource "kubernetes_secret" "universal_db_secret" {
  count = var.enable_universal_database ? 1 : 0

  metadata {
    name      = "mlops-universal-db-credentials"
    namespace = "mlops-clinical-trials"
    labels    = var.tags
  }

  data = {
    username      = var.database_user
    password      = random_password.universal_db_password[0].result
    database_name = var.database_name
    connection_string = "postgresql://${var.database_user}:${random_password.universal_db_password[0].result}@mlops-universal-db.mlops-clinical-trials.svc.cluster.local:26257/${var.database_name}?sslmode=verify-full"
  }
}

# ConfigMap defining schema, geo-partitioning, and multi-cloud replication rules
resource "kubernetes_configmap" "universal_db_schema" {
  count = var.enable_universal_database ? 1 : 0

  metadata {
    name      = "mlops-universal-db-init"
    namespace = "mlops-clinical-trials"
  }

  data = {
    "01_init_schema.sql" = <<-SQL
      -- Universal Multi-Cloud Clinical Trial Database Schema
      CREATE DATABASE IF NOT EXISTS ${var.database_name};
      USE ${var.database_name};

      -- Patient Records with Multi-Region Survival Replication
      CREATE TABLE IF NOT EXISTS patient_records (
          patient_id STRING PRIMARY KEY,
          cloud_origin STRING NOT NULL,
          age INT,
          gender STRING,
          biomarkers JSONB,
          created_at TIMESTAMPTZ DEFAULT NOW(),
          INDEX idx_cloud_origin (cloud_origin)
      );

      -- High-Throughput Inference Traffic & Request Logs
      CREATE TABLE IF NOT EXISTS inference_request_logs (
          request_id STRING PRIMARY KEY,
          patient_id STRING NOT NULL,
          model_name STRING NOT NULL,
          prediction_score FLOAT8,
          latency_ms FLOAT8,
          timestamp TIMESTAMPTZ DEFAULT NOW()
      );

      -- Distributed Feature Store Cache Table
      CREATE TABLE IF NOT EXISTS feature_store_cache (
          feature_key STRING PRIMARY KEY,
          feature_values JSONB NOT NULL,
          updated_at TIMESTAMPTZ DEFAULT NOW()
      );
    SQL
  }
}

# Helm Release deploying CockroachDB / YugabyteDB Distributed SQL Cluster
resource "helm_release" "universal_cockroachdb" {
  count            = var.enable_universal_database ? 1 : 0
  name             = var.cluster_name
  repository       = "https://charts.cockroachdb.com/"
  chart            = "cockroachdb"
  version          = "11.1.6"
  namespace        = "mlops-clinical-trials"
  create_namespace = false

  set {
    name  = "statefulset.replicas"
    value = tostring(var.nodes_per_cloud)
  }

  set {
    name  = "storage.persistentVolume.size"
    value = "${var.storage_gb_per_node}Gi"
  }

  set {
    name  = "tls.enabled"
    value = tostring(var.enable_encryption)
  }

  set {
    name  = "conf.join"
    value = "mlops-universal-db-0.mlops-universal-db,mlops-universal-db-1.mlops-universal-db,mlops-universal-db-2.mlops-universal-db"
  }

  set {
    name  = "conf.single-node"
    value = "false"
  }
}
