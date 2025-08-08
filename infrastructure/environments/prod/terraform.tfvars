# Production Environment Variables
environment = "prod"
cost_center = "mlops-production"

# Cloud Provider Configurations
azure_subscription_id = "your-azure-subscription-id"
gcp_project_id        = "your-gcp-project-id"

# AWS Configuration
aws_region           = "us-west-2"
aws_secondary_region = "us-east-1"

# Azure Configuration  
azure_region           = "West US 2"
azure_secondary_region = "East US 2"

# GCP Configuration
gcp_region           = "us-central1"
gcp_zone            = "us-central1-a"
gcp_secondary_region = "us-east1"

# Production Instance Types (Performance-optimized)
aws_instance_types = {
  general = "m5.xlarge"
  compute = "c5.2xlarge"
  memory  = "r5.xlarge"
  gpu     = "p3.8xlarge"
}

azure_vm_sizes = {
  general = "Standard_D4s_v3"
  compute = "Standard_F8s_v2"
  memory  = "Standard_E4s_v3"
  gpu     = "Standard_NC12s_v3"
}

gcp_machine_types = {
  general = "e2-standard-4"
  compute = "c2-standard-8"
  memory  = "n2-highmem-4"
  gpu     = "n1-standard-8"
}

# Production Features
enable_multi_region     = true
enable_disaster_recovery = true

# Auto-scaling Configuration (Production-grade)
autoscaling_config = {
  min_size                = 3
  max_size                = 20
  desired_capacity        = 6
  scale_up_threshold      = 70
  scale_down_threshold    = 30
  enable_cluster_autoscaler = true
}

# Database Configuration (Production-grade)
database_config = {
  engine_version    = "15.4"
  instance_class    = "db.r5.2xlarge"
  allocated_storage = 500
  backup_retention  = 30
  multi_az         = true
  encrypt_storage  = true
}

# Redis Configuration (Production-grade)
redis_config = {
  node_type           = "cache.r5.xlarge"
  num_cache_nodes    = 3
  parameter_group    = "default.redis7"
  port               = 6379
  engine_version     = "7.0"
}

# Monitoring Configuration (Full observability)
monitoring_config = {
  enable_prometheus = true
  enable_grafana   = true
  enable_jaeger    = true
  enable_elk_stack = true
  retention_days   = 90
}

# Security Configuration (Maximum security)
security_config = {
  enable_encryption_at_rest   = true
  enable_encryption_in_transit = true
  enable_waf                  = true
  enable_ddos_protection     = true
  enable_secret_management   = true
  enable_audit_logging       = true
}

# Backup Configuration (Comprehensive backup)
backup_config = {
  enable_automated_backups = true
  backup_retention_days   = 30
  enable_cross_region_backup = true
  enable_point_in_time_recovery = true
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
}

# Network Configuration
network_config = {
  vpc_cidr                = "10.0.0.0/16"
  public_subnet_cidrs     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs    = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]
  database_subnet_cidrs   = ["10.0.20.0/24", "10.0.21.0/24", "10.0.22.0/24"]
  enable_nat_gateway      = true
  enable_vpn_gateway      = false
  enable_flow_logs        = true
}
