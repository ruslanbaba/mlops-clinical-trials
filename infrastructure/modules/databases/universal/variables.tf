# Universal Multi-Cloud Database Module Variables

variable "environment" {
  description = "Target environment (dev, staging, prod)"
  type        = string
}

variable "cluster_name" {
  description = "Universal multi-cloud database cluster name"
  type        = string
  default     = "mlops-universal-db"
}

variable "enable_universal_database" {
  description = "Flag to enable optional universal multi-cloud database"
  type        = bool
  default     = true
}

variable "nodes_per_cloud" {
  description = "Number of database nodes per cloud provider (AWS, Azure, GCP)"
  type        = number
  default     = 3
}

variable "storage_gb_per_node" {
  description = "Storage volume size in GB per database node"
  type        = number
  default     = 100
}

variable "database_name" {
  description = "Default database name for MLOps clinical trial data"
  type        = string
  default     = "mlops_clinical_trials_universal"
}

variable "database_user" {
  description = "Database master admin user"
  type        = string
  default     = "universal_admin"
}

variable "enable_encryption" {
  description = "Enable at-rest and in-transit TLS encryption"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}
