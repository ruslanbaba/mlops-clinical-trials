# Development Environment Configuration

terraform {
  required_version = ">= 1.6.0"
  
  backend "s3" {
    bucket         = "mlops-clinical-trials-tfstate-dev"
    key            = "environments/dev/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-locks-dev"
  }
}

# Include all provider configurations
module "aws_infrastructure" {
  source = "../../providers/aws"
  
  # Environment-specific variables
  environment = "dev"
  cost_center = "mlops-development"
  
  # AWS Configuration
  aws_region           = "us-west-2"
  aws_secondary_region = "us-east-1"
  
  # Smaller instances for development
  aws_instance_types = {
    general = "t3.medium"
    compute = "c5.large"
    memory  = "r5.large"
    gpu     = "p3.2xlarge"
  }
  
  # Development-specific settings
  enable_multi_region     = false
  enable_disaster_recovery = false
  
  # Reduced capacity for development
  autoscaling_config = {
    min_size                = 1
    max_size                = 5
    desired_capacity        = 2
    scale_up_threshold      = 80
    scale_down_threshold    = 20
    enable_cluster_autoscaler = true
  }
  
  # Basic monitoring for development
  monitoring_config = {
    enable_prometheus = true
    enable_grafana   = true
    enable_jaeger    = false
    enable_elk_stack = false
    retention_days   = 7
  }
  
  # Relaxed security for development
  security_config = {
    enable_encryption_at_rest   = true
    enable_encryption_in_transit = true
    enable_waf                  = false
    enable_ddos_protection     = false
    enable_secret_management   = true
    enable_audit_logging       = false
  }
  
  # Minimal backup configuration
  backup_config = {
    enable_automated_backups = true
    backup_retention_days   = 7
    enable_cross_region_backup = false
    enable_point_in_time_recovery = false
    backup_window          = "03:00-04:00"
    maintenance_window     = "sun:04:00-sun:05:00"
  }
}

module "azure_infrastructure" {
  source = "../../providers/azure"
  
  # Environment-specific variables
  environment = "dev"
  cost_center = "mlops-development"
  
  # Azure Configuration
  azure_subscription_id    = var.azure_subscription_id
  azure_region            = "West US 2"
  azure_secondary_region  = "East US 2"
  
  # Smaller VMs for development
  azure_vm_sizes = {
    general = "Standard_B2s"
    compute = "Standard_F2s_v2"
    memory  = "Standard_E2s_v3"
    gpu     = "Standard_NC6s_v3"
  }
  
  # Same configuration as AWS for consistency
  enable_multi_region     = false
  enable_disaster_recovery = false
  autoscaling_config      = module.aws_infrastructure.autoscaling_config
  monitoring_config       = module.aws_infrastructure.monitoring_config
  security_config         = module.aws_infrastructure.security_config
  backup_config          = module.aws_infrastructure.backup_config
}

module "gcp_infrastructure" {
  source = "../../providers/gcp"
  
  # Environment-specific variables
  environment = "dev"
  cost_center = "mlops-development"
  
  # GCP Configuration
  gcp_project_id       = var.gcp_project_id
  gcp_region          = "us-central1"
  gcp_zone            = "us-central1-a"
  gcp_secondary_region = "us-east1"
  
  # Smaller machines for development
  gcp_machine_types = {
    general = "e2-small"
    compute = "c2-standard-2"
    memory  = "n2-highmem-2"
    gpu     = "n1-standard-2"
  }
  
  # Same configuration as AWS for consistency
  enable_multi_region     = false
  enable_disaster_recovery = false
  autoscaling_config      = module.aws_infrastructure.autoscaling_config
  monitoring_config       = module.aws_infrastructure.monitoring_config
  security_config         = module.aws_infrastructure.security_config
  backup_config          = module.aws_infrastructure.backup_config
}
