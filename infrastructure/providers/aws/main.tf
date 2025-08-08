# AWS EKS Cluster Configuration
module "aws_eks" {
  source = "../modules/kubernetes/aws"
  
  cluster_name    = local.aws_cluster_name
  cluster_version = var.aws_eks_version
  
  vpc_id     = module.aws_vpc.vpc_id
  subnet_ids = module.aws_vpc.private_subnet_ids
  
  node_groups = {
    general = {
      instance_types = [var.aws_instance_types.general]
      min_size      = var.autoscaling_config.min_size
      max_size      = var.autoscaling_config.max_size
      desired_size  = var.autoscaling_config.desired_capacity
    }
    compute = {
      instance_types = [var.aws_instance_types.compute]
      min_size      = 0
      max_size      = 5
      desired_size  = 1
      taints = [{
        key    = "workload-type"
        value  = "compute-intensive"
        effect = "NO_SCHEDULE"
      }]
    }
    gpu = {
      instance_types = [var.aws_instance_types.gpu]
      min_size      = 0
      max_size      = 3
      desired_size  = 0
      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }
  
  tags = local.common_tags
}

# AWS VPC Configuration
module "aws_vpc" {
  source = "../modules/networking/aws"
  
  name                 = "mlops-vpc-${local.resource_suffix}"
  cidr                 = var.network_config.vpc_cidr
  availability_zones   = data.aws_availability_zones.available.names
  
  public_subnets       = var.network_config.public_subnet_cidrs
  private_subnets      = var.network_config.private_subnet_cidrs
  database_subnets     = var.network_config.database_subnet_cidrs
  
  enable_nat_gateway   = var.network_config.enable_nat_gateway
  enable_vpn_gateway   = var.network_config.enable_vpn_gateway
  enable_flow_logs     = var.network_config.enable_flow_logs
  
  tags = local.common_tags
}

# AWS RDS Aurora PostgreSQL
module "aws_rds" {
  source = "../modules/databases/aws"
  
  identifier     = "mlops-aurora-${local.resource_suffix}"
  engine         = "aurora-postgresql"
  engine_version = var.database_config.engine_version
  
  database_name = local.database_name
  master_username = "postgres"
  
  vpc_id               = module.aws_vpc.vpc_id
  subnet_ids           = module.aws_vpc.database_subnet_ids
  vpc_security_group_ids = [module.aws_security.database_security_group_id]
  
  instance_class       = var.database_config.instance_class
  instances_count      = var.environment == "prod" ? 3 : 1
  
  backup_retention_period = var.database_config.backup_retention
  backup_window          = var.backup_config.backup_window
  maintenance_window     = var.backup_config.maintenance_window
  
  monitoring_interval = 60
  performance_insights_enabled = true
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  tags = local.common_tags
}

# AWS ElastiCache Redis
module "aws_elasticache" {
  source = "../modules/storage/aws/elasticache"
  
  cluster_id         = "mlops-redis-${local.resource_suffix}"
  node_type          = var.redis_config.node_type
  num_cache_nodes    = var.redis_config.num_cache_nodes
  parameter_group_name = var.redis_config.parameter_group
  port               = var.redis_config.port
  engine_version     = var.redis_config.engine_version
  
  subnet_group_name = module.aws_vpc.elasticache_subnet_group_name
  security_group_ids = [module.aws_security.redis_security_group_id]
  
  apply_immediately     = var.environment != "prod"
  auto_minor_version_upgrade = true
  
  tags = local.common_tags
}

# AWS S3 Storage
module "aws_s3" {
  source = "../modules/storage/aws/s3"
  
  bucket_name = local.aws_bucket_name
  
  versioning_enabled = true
  encryption_enabled = var.security_config.enable_encryption_at_rest
  
  lifecycle_rules = [
    {
      id     = "intelligent_tiering"
      status = "Enabled"
      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        },
        {
          days          = 365
          storage_class = "DEEP_ARCHIVE"
        }
      ]
    }
  ]
  
  cross_region_replication = var.enable_disaster_recovery ? {
    enabled = true
    destination_bucket = "${local.aws_bucket_name}-dr"
    destination_region = var.aws_secondary_region
  } : null
  
  tags = local.common_tags
}

# AWS Security Groups and IAM
module "aws_security" {
  source = "../modules/security/aws"
  
  vpc_id = module.aws_vpc.vpc_id
  environment = var.environment
  
  enable_waf = var.security_config.enable_waf
  enable_encryption = var.security_config.enable_encryption_at_rest
  
  tags = local.common_tags
}

# AWS SageMaker Integration
module "aws_sagemaker" {
  source = "../modules/ml/aws/sagemaker"
  
  domain_name = "mlops-clinical-trials-${local.resource_suffix}"
  
  vpc_id     = module.aws_vpc.vpc_id
  subnet_ids = module.aws_vpc.private_subnet_ids
  
  execution_role_name = "SageMakerExecutionRole-${local.resource_suffix}"
  
  default_user_settings = {
    execution_role  = module.aws_security.sagemaker_execution_role_arn
    security_groups = [module.aws_security.sagemaker_security_group_id]
  }
  
  tags = local.common_tags
}

# AWS Load Balancer Controller
resource "aws_iam_role" "aws_load_balancer_controller" {
  name = "AmazonEKSLoadBalancerControllerRole-${local.resource_suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = module.aws_eks.oidc_provider_arn
        }
        Condition = {
          StringEquals = {
            "${replace(module.aws_eks.oidc_provider_url, "https://", "")}:sub": "system:serviceaccount:kube-system:aws-load-balancer-controller"
            "${replace(module.aws_eks.oidc_provider_url, "https://", "")}:aud": "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "aws_load_balancer_controller" {
  policy_arn = "arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess"
  role       = aws_iam_role.aws_load_balancer_controller.name
}
