# Azure Resource Group
resource "azurerm_resource_group" "main" {
  name     = "rg-mlops-clinical-trials-${local.resource_suffix}"
  location = var.azure_region
  
  tags = local.common_tags
}

# Azure AKS Cluster
module "azure_aks" {
  source = "../modules/kubernetes/azure"
  
  cluster_name        = local.azure_cluster_name
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  
  kubernetes_version = var.azure_aks_version
  
  vnet_subnet_id = module.azure_vnet.aks_subnet_id
  
  default_node_pool = {
    name                = "general"
    vm_size            = var.azure_vm_sizes.general
    node_count         = var.autoscaling_config.desired_capacity
    min_count          = var.autoscaling_config.min_size
    max_count          = var.autoscaling_config.max_size
    enable_auto_scaling = true
    availability_zones  = ["1", "2", "3"]
  }
  
  additional_node_pools = {
    compute = {
      name               = "compute"
      vm_size           = var.azure_vm_sizes.compute
      node_count        = 1
      min_count         = 0
      max_count         = 5
      enable_auto_scaling = true
      node_taints       = ["workload-type=compute-intensive:NoSchedule"]
    }
    gpu = {
      name               = "gpu"
      vm_size           = var.azure_vm_sizes.gpu
      node_count        = 0
      min_count         = 0
      max_count         = 3
      enable_auto_scaling = true
      node_taints       = ["nvidia.com/gpu=true:NoSchedule"]
    }
  }
  
  # Azure AD integration
  azure_rbac_enabled = true
  local_account_disabled = true
  
  # Monitoring and logging
  oms_agent_enabled = true
  log_analytics_workspace_id = module.azure_monitoring.log_analytics_workspace_id
  
  tags = local.common_tags
}

# Azure Virtual Network
module "azure_vnet" {
  source = "../modules/networking/azure"
  
  vnet_name           = "vnet-mlops-${local.resource_suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  
  address_space = [var.network_config.vpc_cidr]
  
  subnets = {
    aks = {
      address_prefixes = [var.network_config.private_subnet_cidrs[0]]
    }
    database = {
      address_prefixes = [var.network_config.database_subnet_cidrs[0]]
      delegation = [{
        name = "Microsoft.DBforPostgreSQL/flexibleServers"
        service_delegation = {
          name = "Microsoft.DBforPostgreSQL/flexibleServers"
          actions = [
            "Microsoft.Network/virtualNetworks/subnets/join/action"
          ]
        }
      }]
    }
    private_endpoints = {
      address_prefixes = [var.network_config.private_subnet_cidrs[1]]
    }
    application_gateway = {
      address_prefixes = [var.network_config.public_subnet_cidrs[0]]
    }
  }
  
  enable_ddos_protection = var.security_config.enable_ddos_protection
  
  tags = local.common_tags
}

# Azure PostgreSQL Flexible Server
module "azure_postgresql" {
  source = "../modules/databases/azure"
  
  server_name         = "psql-mlops-${local.resource_suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  
  sku_name = "GP_Standard_D2s_v3"
  version  = "15"
  
  storage_mb = var.database_config.allocated_storage * 1024
  backup_retention_days = var.database_config.backup_retention
  
  delegated_subnet_id = module.azure_vnet.database_subnet_id
  private_dns_zone_id = azurerm_private_dns_zone.postgresql.id
  
  high_availability = {
    mode                      = var.environment == "prod" ? "ZoneRedundant" : "SameZone"
    standby_availability_zone = var.environment == "prod" ? "2" : null
  }
  
  administrator_login    = "postgres"
  administrator_password = random_password.postgresql_password.result
  
  databases = [
    {
      name      = local.database_name
      charset   = "UTF8"
      collation = "en_US.utf8"
    }
  ]
  
  tags = local.common_tags
}

# Azure Cache for Redis
module "azure_redis" {
  source = "../modules/storage/azure/redis"
  
  name                = "redis-mlops-${local.resource_suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  
  capacity            = 1
  family              = "C"
  sku_name           = "Standard"
  enable_non_ssl_port = false
  
  redis_version = "6"
  
  subnet_id = module.azure_vnet.private_endpoints_subnet_id
  
  redis_configuration = {
    maxmemory_reserved = "10"
    maxmemory_delta    = "10"
    maxmemory_policy   = "allkeys-lru"
  }
  
  tags = local.common_tags
}

# Azure Storage Account
module "azure_storage" {
  source = "../modules/storage/azure/storage_account"
  
  storage_account_name = local.azure_storage_name
  resource_group_name  = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  
  account_tier             = "Standard"
  account_replication_type = var.enable_disaster_recovery ? "GRS" : "LRS"
  
  containers = [
    {
      name        = "models"
      access_type = "private"
    },
    {
      name        = "data"
      access_type = "private"
    },
    {
      name        = "artifacts"
      access_type = "private"
    }
  ]
  
  enable_https_traffic_only = true
  min_tls_version          = "TLS1_2"
  
  # Data Lake Gen2
  is_hns_enabled = true
  
  tags = local.common_tags
}

# Azure Machine Learning Workspace
module "azure_ml" {
  source = "../modules/ml/azure"
  
  workspace_name      = "mlw-clinical-trials-${local.resource_suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  
  storage_account_id = module.azure_storage.storage_account_id
  key_vault_id      = module.azure_security.key_vault_id
  
  application_insights = {
    name                = "ai-mlops-${local.resource_suffix}"
    application_type    = "web"
    retention_in_days   = 30
  }
  
  compute_instances = {
    cpu_cluster = {
      name         = "cpu-cluster"
      vm_size      = var.azure_vm_sizes.compute
      min_nodes    = 0
      max_nodes    = 10
    }
    gpu_cluster = {
      name         = "gpu-cluster"
      vm_size      = var.azure_vm_sizes.gpu
      min_nodes    = 0
      max_nodes    = 5
    }
  }
  
  tags = local.common_tags
}

# Azure Monitoring and Logging
module "azure_monitoring" {
  source = "../modules/monitoring/azure"
  
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  
  log_analytics_workspace = {
    name              = "log-mlops-${local.resource_suffix}"
    sku               = "PerGB2018"
    retention_in_days = var.monitoring_config.retention_days
  }
  
  application_insights = {
    name             = "ai-mlops-${local.resource_suffix}"
    application_type = "web"
  }
  
  tags = local.common_tags
}

# Azure Security (Key Vault, etc.)
module "azure_security" {
  source = "../modules/security/azure"
  
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  
  key_vault = {
    name                     = "kv-mlops-${random_id.suffix.hex}"
    sku_name                = "standard"
    purge_protection_enabled = var.environment == "prod"
  }
  
  tags = local.common_tags
}

# Azure Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "postgresql" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name
  
  tags = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgresql" {
  name                  = "postgresql-vnet-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgresql.name
  virtual_network_id    = module.azure_vnet.vnet_id
  resource_group_name   = azurerm_resource_group.main.name
  registration_enabled  = false
  
  tags = local.common_tags
}

# Random password for PostgreSQL
resource "random_password" "postgresql_password" {
  length  = 16
  special = true
}
