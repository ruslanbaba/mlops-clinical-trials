# Universal Multi-Cloud Database Module Outputs

output "database_name" {
  description = "Name of the universal database"
  value       = var.database_name
}

output "database_user" {
  description = "Master username for universal database"
  value       = var.database_user
}

output "database_password_secret_name" {
  description = "Kubernetes Secret name storing universal database credentials"
  value       = var.enable_universal_database ? kubernetes_secret.universal_db_secret[0].metadata[0].name : null
}

output "connection_endpoint" {
  description = "Internal Kubernetes connection endpoint for the universal database"
  value       = "mlops-universal-db.mlops-clinical-trials.svc.cluster.local:26257"
}

output "is_enabled" {
  description = "Indicates whether the universal database is active"
  value       = var.enable_universal_database
}
