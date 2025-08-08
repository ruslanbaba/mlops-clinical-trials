# Production Environment Configuration

terraform {
  required_version = ">= 1.6.0"
  
  backend "s3" {
    bucket         = "mlops-clinical-trials-tfstate-prod"
    key            = "environments/prod/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-locks-prod"
  }
}

# Production AWS Infrastructure
module "aws_infrastructure" {
  source = "../../providers/aws"
  
  # Environment-specific variables
  environment = "prod"
  cost_center = "mlops-production"
  
  # AWS Configuration
  aws_region           = "us-west-2"
  aws_secondary_region = "us-east-1"
  
  # Production-grade instances
  aws_instance_types = {
    general = "m5.xlarge"
    compute = "c5.2xlarge"
    memory  = "r5.xlarge"
    gpu     = "p3.8xlarge"
  }
  
  # Multi-region production deployment
  enable_multi_region     = true
  enable_disaster_recovery = true
  
  # Production scaling configuration
  autoscaling_config = {
    min_size                = 3
    max_size                = 20
    desired_capacity        = 6
    scale_up_threshold      = 70
    scale_down_threshold    = 30
    enable_cluster_autoscaler = true
  }
  
  # Full monitoring stack
  monitoring_config = {
    enable_prometheus = true
    enable_grafana   = true
    enable_jaeger    = true
    enable_elk_stack = true
    retention_days   = 90
  }
  
  # Maximum security for production
  security_config = {
    enable_encryption_at_rest   = true
    enable_encryption_in_transit = true
    enable_waf                  = true
    enable_ddos_protection     = true
    enable_secret_management   = true
    enable_audit_logging       = true
  }
  
  # Comprehensive backup strategy
  backup_config = {
    enable_automated_backups = true
    backup_retention_days   = 30
    enable_cross_region_backup = true
    enable_point_in_time_recovery = true
    backup_window          = "03:00-04:00"
    maintenance_window     = "sun:04:00-sun:05:00"
  }
  
  # Production database configuration
  database_config = {
    engine_version    = "15.4"
    instance_class    = "db.r5.2xlarge"
    allocated_storage = 500
    backup_retention  = 30
    multi_az         = true
    encrypt_storage  = true
  }
  
  # Production Redis configuration
  redis_config = {
    node_type           = "cache.r5.xlarge"
    num_cache_nodes    = 3
    parameter_group    = "default.redis7"
    port               = 6379
    engine_version     = "7.0"
  }
}

# Production Azure Infrastructure
module "azure_infrastructure" {
  source = "../../providers/azure"
  
  # Environment-specific variables
  environment = "prod"
  cost_center = "mlops-production"
  
  # Azure Configuration
  azure_subscription_id    = var.azure_subscription_id
  azure_region            = "West US 2"
  azure_secondary_region  = "East US 2"
  
  # Production-grade VMs
  azure_vm_sizes = {
    general = "Standard_D4s_v3"
    compute = "Standard_F8s_v2"
    memory  = "Standard_E4s_v3"
    gpu     = "Standard_NC12s_v3"
  }
  
  # Multi-region production deployment
  enable_multi_region     = true
  enable_disaster_recovery = true
  
  # Same production configurations
  autoscaling_config = module.aws_infrastructure.autoscaling_config
  monitoring_config  = module.aws_infrastructure.monitoring_config
  security_config    = module.aws_infrastructure.security_config
  backup_config     = module.aws_infrastructure.backup_config
  database_config   = module.aws_infrastructure.database_config
  redis_config      = module.aws_infrastructure.redis_config
}

# Production GCP Infrastructure
module "gcp_infrastructure" {
  source = "../../providers/gcp"
  
  # Environment-specific variables
  environment = "prod"
  cost_center = "mlops-production"
  
  # GCP Configuration
  gcp_project_id       = var.gcp_project_id
  gcp_region          = "us-central1"
  gcp_zone            = "us-central1-a"
  gcp_secondary_region = "us-east1"
  
  # Production-grade machines
  gcp_machine_types = {
    general = "e2-standard-4"
    compute = "c2-standard-8"
    memory  = "n2-highmem-4"
    gpu     = "n1-standard-8"
  }
  
  # Multi-region production deployment
  enable_multi_region     = true
  enable_disaster_recovery = true
  
  # Same production configurations
  autoscaling_config = module.aws_infrastructure.autoscaling_config
  monitoring_config  = module.aws_infrastructure.monitoring_config
  security_config    = module.aws_infrastructure.security_config
  backup_config     = module.aws_infrastructure.backup_config
  database_config   = module.aws_infrastructure.database_config
  redis_config      = module.aws_infrastructure.redis_config
}

# Multi-cloud DNS and Traffic Management
module "global_dns" {
  source = "../../modules/networking/global"
  
  domain_name = "mlops-clinical-trials.com"
  
  # Multi-cloud load balancing
  endpoints = {
    aws = {
      region   = module.aws_infrastructure.primary_region
      endpoint = module.aws_infrastructure.load_balancer_dns
      weight   = 34
    }
    azure = {
      region   = module.azure_infrastructure.primary_region
      endpoint = module.azure_infrastructure.load_balancer_dns
      weight   = 33
    }
    gcp = {
      region   = module.gcp_infrastructure.primary_region
      endpoint = module.gcp_infrastructure.load_balancer_dns
      weight   = 33
    }
  }
  
  # Health checks for each cloud
  health_checks = {
    aws   = "${module.aws_infrastructure.load_balancer_dns}/health"
    azure = "${module.azure_infrastructure.load_balancer_dns}/health"
    gcp   = "${module.gcp_infrastructure.load_balancer_dns}/health"
  }
  
  # Failover configuration
  failover_policy = {
    primary_targets = ["aws", "azure", "gcp"]
    backup_targets  = []
  }
}

# Cross-cloud monitoring and alerting
module "global_monitoring" {
  source = "../../modules/monitoring/global"
  
  # Aggregate metrics from all clouds
  data_sources = {
    aws_prometheus   = module.aws_infrastructure.prometheus_endpoint
    azure_prometheus = module.azure_infrastructure.prometheus_endpoint
    gcp_prometheus   = module.gcp_infrastructure.prometheus_endpoint
  }
  
  # Global alerting rules
  alert_rules = [
    {
      name        = "MultiCloudServiceDown"
      description = "Service is down in multiple clouds"
      condition   = "sum(up{job='api-server'}) < 2"
      severity    = "critical"
    },
    {
      name        = "CrossCloudLatencyHigh"
      description = "High latency across cloud providers"
      condition   = "avg(api_request_duration_seconds) > 1"
      severity    = "warning"
    }
  ]
  
  # Notification channels
  notification_channels = [
    {
      type   = "slack"
      config = { webhook_url = var.slack_webhook_url }
    },
    {
      type   = "pagerduty"
      config = { service_key = var.pagerduty_service_key }
    }
  ]
}
