# Global Variables
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "cost_center" {
  description = "Cost center for resource tagging"
  type        = string
  default     = "mlops-research"
}

variable "enable_multi_region" {
  description = "Enable multi-region deployment"
  type        = bool
  default     = false
}

variable "enable_disaster_recovery" {
  description = "Enable disaster recovery features"
  type        = bool
  default     = false
}

# AWS Variables
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "aws_secondary_region" {
  description = "AWS secondary region for disaster recovery"
  type        = string
  default     = "us-east-1"
}

variable "aws_instance_types" {
  description = "EC2 instance types for different workloads"
  type = object({
    general    = string
    compute    = string
    memory     = string
    gpu        = string
  })
  default = {
    general = "m5.large"
    compute = "c5.xlarge"
    memory  = "r5.large"
    gpu     = "p3.2xlarge"
  }
}

variable "aws_eks_version" {
  description = "EKS cluster version"
  type        = string
  default     = "1.28"
}

# Azure Variables
variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "azure_region" {
  description = "Azure region for resources"
  type        = string
  default     = "West US 2"
}

variable "azure_secondary_region" {
  description = "Azure secondary region for disaster recovery"
  type        = string
  default     = "East US 2"
}

variable "azure_vm_sizes" {
  description = "Azure VM sizes for different workloads"
  type = object({
    general = string
    compute = string
    memory  = string
    gpu     = string
  })
  default = {
    general = "Standard_D2s_v3"
    compute = "Standard_F4s_v2"
    memory  = "Standard_E2s_v3"
    gpu     = "Standard_NC6s_v3"
  }
}

variable "azure_aks_version" {
  description = "AKS cluster version"
  type        = string
  default     = "1.28"
}

# GCP Variables
variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "gcp_zone" {
  description = "GCP zone for resources"
  type        = string
  default     = "us-central1-a"
}

variable "gcp_secondary_region" {
  description = "GCP secondary region for disaster recovery"
  type        = string
  default     = "us-east1"
}

variable "gcp_machine_types" {
  description = "GCP machine types for different workloads"
  type = object({
    general = string
    compute = string
    memory  = string
    gpu     = string
  })
  default = {
    general = "e2-standard-2"
    compute = "c2-standard-4"
    memory  = "n2-highmem-2"
    gpu     = "n1-standard-4"
  }
}

variable "gcp_gke_version" {
  description = "GKE cluster version"
  type        = string
  default     = "1.28"
}

# Kubernetes Configuration
variable "kubernetes_namespace" {
  description = "Kubernetes namespace for application deployment"
  type        = string
  default     = "mlops-clinical-trials"
}

# Database Configuration
variable "database_config" {
  description = "Database configuration"
  type = object({
    engine_version    = string
    instance_class    = string
    allocated_storage = number
    backup_retention  = number
    multi_az         = bool
    encrypt_storage  = bool
  })
  default = {
    engine_version    = "15.4"
    instance_class    = "db.r5.large"
    allocated_storage = 100
    backup_retention  = 7
    multi_az         = true
    encrypt_storage  = true
  }
}

# Redis Configuration
variable "redis_config" {
  description = "Redis configuration"
  type = object({
    node_type           = string
    num_cache_nodes    = number
    parameter_group    = string
    port               = number
    engine_version     = string
  })
  default = {
    node_type           = "cache.r5.large"
    num_cache_nodes    = 2
    parameter_group    = "default.redis7"
    port               = 6379
    engine_version     = "7.0"
  }
}

# Monitoring Configuration
variable "monitoring_config" {
  description = "Monitoring and observability configuration"
  type = object({
    enable_prometheus     = bool
    enable_grafana       = bool
    enable_jaeger        = bool
    enable_elk_stack     = bool
    retention_days       = number
  })
  default = {
    enable_prometheus = true
    enable_grafana   = true
    enable_jaeger    = true
    enable_elk_stack = true
    retention_days   = 30
  }
}

# Security Configuration
variable "security_config" {
  description = "Security configuration"
  type = object({
    enable_encryption_at_rest   = bool
    enable_encryption_in_transit = bool
    enable_waf                  = bool
    enable_ddos_protection     = bool
    enable_secret_management   = bool
    enable_audit_logging       = bool
  })
  default = {
    enable_encryption_at_rest   = true
    enable_encryption_in_transit = true
    enable_waf                  = true
    enable_ddos_protection     = true
    enable_secret_management   = true
    enable_audit_logging       = true
  }
}

# Networking Configuration
variable "network_config" {
  description = "Network configuration"
  type = object({
    vpc_cidr                = string
    public_subnet_cidrs     = list(string)
    private_subnet_cidrs    = list(string)
    database_subnet_cidrs   = list(string)
    enable_nat_gateway      = bool
    enable_vpn_gateway      = bool
    enable_flow_logs        = bool
  })
  default = {
    vpc_cidr                = "10.0.0.0/16"
    public_subnet_cidrs     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
    private_subnet_cidrs    = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]
    database_subnet_cidrs   = ["10.0.20.0/24", "10.0.21.0/24", "10.0.22.0/24"]
    enable_nat_gateway      = true
    enable_vpn_gateway      = false
    enable_flow_logs        = true
  }
}

# Auto-scaling Configuration
variable "autoscaling_config" {
  description = "Auto-scaling configuration"
  type = object({
    min_size                = number
    max_size                = number
    desired_capacity        = number
    scale_up_threshold      = number
    scale_down_threshold    = number
    enable_cluster_autoscaler = bool
  })
  default = {
    min_size                = 1
    max_size                = 10
    desired_capacity        = 3
    scale_up_threshold      = 70
    scale_down_threshold    = 30
    enable_cluster_autoscaler = true
  }
}

# Backup Configuration
variable "backup_config" {
  description = "Backup and disaster recovery configuration"
  type = object({
    enable_automated_backups = bool
    backup_retention_days   = number
    enable_cross_region_backup = bool
    enable_point_in_time_recovery = bool
    backup_window          = string
    maintenance_window     = string
  })
  default = {
    enable_automated_backups = true
    backup_retention_days   = 30
    enable_cross_region_backup = true
    enable_point_in_time_recovery = true
    backup_window          = "03:00-04:00"
    maintenance_window     = "sun:04:00-sun:05:00"
  }
}
