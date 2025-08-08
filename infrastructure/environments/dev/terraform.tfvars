# Development Environment Variables
environment = "dev"
cost_center = "mlops-development"

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

# Development Instance Types (Cost-optimized)
aws_instance_types = {
  general = "t3.medium"
  compute = "c5.large"
  memory  = "r5.large"
  gpu     = "p3.2xlarge"
}

azure_vm_sizes = {
  general = "Standard_B2s"
  compute = "Standard_F2s_v2"
  memory  = "Standard_E2s_v3"
  gpu     = "Standard_NC6s_v3"
}

gcp_machine_types = {
  general = "e2-small"
  compute = "c2-standard-2"
  memory  = "n2-highmem-2"
  gpu     = "n1-standard-2"
}

# Development Features
enable_multi_region     = false
enable_disaster_recovery = false

# Auto-scaling Configuration (Minimal for dev)
autoscaling_config = {
  min_size                = 1
  max_size                = 5
  desired_capacity        = 2
  scale_up_threshold      = 80
  scale_down_threshold    = 20
  enable_cluster_autoscaler = true
}

# Database Configuration (Smaller for dev)
database_config = {
  engine_version    = "15.4"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  backup_retention  = 7
  multi_az         = false
  encrypt_storage  = true
}

# Redis Configuration (Minimal for dev)
redis_config = {
  node_type           = "cache.t3.micro"
  num_cache_nodes    = 1
  parameter_group    = "default.redis7"
  port               = 6379
  engine_version     = "7.0"
}

# Monitoring Configuration (Basic for dev)
monitoring_config = {
  enable_prometheus = true
  enable_grafana   = true
  enable_jaeger    = false
  enable_elk_stack = false
  retention_days   = 7
}

# Security Configuration (Relaxed for dev)
security_config = {
  enable_encryption_at_rest   = true
  enable_encryption_in_transit = true
  enable_waf                  = false
  enable_ddos_protection     = false
  enable_secret_management   = true
  enable_audit_logging       = false
}

# Backup Configuration (Minimal for dev)
backup_config = {
  enable_automated_backups = true
  backup_retention_days   = 7
  enable_cross_region_backup = false
  enable_point_in_time_recovery = false
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
  enable_flow_logs        = false
}
