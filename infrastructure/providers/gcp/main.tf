# GCP Project Services
resource "google_project_service" "required_apis" {
  for_each = toset([
    "container.googleapis.com",
    "compute.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "memcache.googleapis.com",
    "servicenetworking.googleapis.com"
  ])
  
  project = var.gcp_project_id
  service = each.value
  
  disable_on_destroy = false
}

# GCP GKE Cluster
module "gcp_gke" {
  source = "../modules/kubernetes/gcp"
  
  project_id = var.gcp_project_id
  region     = var.gcp_region
  
  cluster_name = local.gcp_cluster_name
  
  # Network configuration
  network    = module.gcp_vpc.network_name
  subnetwork = module.gcp_vpc.private_subnet_name
  
  # IP allocation
  ip_range_pods     = "gke-pods"
  ip_range_services = "gke-services"
  
  # Cluster configuration
  kubernetes_version = var.gcp_gke_version
  release_channel    = "STABLE"
  
  # Security
  enable_private_nodes   = true
  enable_private_endpoint = false
  master_ipv4_cidr_block = "172.16.0.0/28"
  
  # Features
  horizontal_pod_autoscaling = true
  network_policy            = true
  istio                     = true
  
  node_pools = [
    {
      name         = "general"
      machine_type = var.gcp_machine_types.general
      
      min_count = var.autoscaling_config.min_size
      max_count = var.autoscaling_config.max_size
      
      disk_size_gb = 100
      disk_type    = "pd-ssd"
      
      auto_repair  = true
      auto_upgrade = true
      
      service_account = module.gcp_security.gke_service_account_email
      
      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
      
      labels = {
        workload-type = "general"
      }
    },
    {
      name         = "compute"
      machine_type = var.gcp_machine_types.compute
      
      min_count = 0
      max_count = 5
      
      disk_size_gb = 100
      disk_type    = "pd-ssd"
      
      auto_repair  = true
      auto_upgrade = true
      
      service_account = module.gcp_security.gke_service_account_email
      
      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
      
      taints = [{
        key    = "workload-type"
        value  = "compute-intensive"
        effect = "NO_SCHEDULE"
      }]
      
      labels = {
        workload-type = "compute"
      }
    },
    {
      name         = "gpu"
      machine_type = var.gcp_machine_types.gpu
      
      min_count = 0
      max_count = 3
      
      disk_size_gb = 100
      disk_type    = "pd-ssd"
      
      auto_repair  = true
      auto_upgrade = true
      
      service_account = module.gcp_security.gke_service_account_email
      
      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
      
      accelerator_count = 1
      accelerator_type  = "nvidia-tesla-k80"
      
      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
      
      labels = {
        workload-type = "gpu"
      }
    }
  ]
  
  node_pools_labels = {
    all = {
      project     = "mlops-clinical-trials"
      environment = var.environment
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# GCP VPC Network
module "gcp_vpc" {
  source = "../modules/networking/gcp"
  
  project_id   = var.gcp_project_id
  network_name = "vpc-mlops-${local.resource_suffix}"
  
  subnets = [
    {
      subnet_name   = "private-subnet"
      subnet_ip     = var.network_config.private_subnet_cidrs[0]
      subnet_region = var.gcp_region
      
      secondary_ranges = [
        {
          range_name    = "gke-pods"
          ip_cidr_range = "192.168.0.0/18"
        },
        {
          range_name    = "gke-services"
          ip_cidr_range = "192.168.64.0/18"
        }
      ]
    },
    {
      subnet_name   = "public-subnet"
      subnet_ip     = var.network_config.public_subnet_cidrs[0]
      subnet_region = var.gcp_region
    }
  ]
  
  routes = [
    {
      name              = "egress-internet"
      description       = "Route to the internet"
      destination_range = "0.0.0.0/0"
      tags              = ["egress-inet"]
      next_hop_internet = "true"
    }
  ]
  
  depends_on = [google_project_service.required_apis]
}

# GCP Cloud SQL PostgreSQL
module "gcp_cloudsql" {
  source = "../modules/databases/gcp"
  
  project_id = var.gcp_project_id
  region     = var.gcp_region
  
  instance_name = "postgresql-mlops-${local.resource_suffix}"
  database_version = "POSTGRES_15"
  
  tier = "db-custom-2-4096"
  
  disk_size = var.database_config.allocated_storage
  disk_type = "PD_SSD"
  
  availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
  
  backup_configuration = {
    enabled                        = true
    start_time                    = "03:00"
    point_in_time_recovery_enabled = true
    transaction_log_retention_days = var.database_config.backup_retention
    backup_retention_settings = {
      retained_backups = var.database_config.backup_retention
      retention_unit   = "COUNT"
    }
  }
  
  maintenance_window = {
    day          = 7  # Sunday
    hour         = 4
    update_track = "stable"
  }
  
  ip_configuration = {
    ipv4_enabled    = false
    private_network = module.gcp_vpc.network_self_link
    require_ssl     = true
  }
  
  database_flags = [
    {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements"
    }
  ]
  
  databases = [
    {
      name = local.database_name
    }
  ]
  
  users = [
    {
      name     = "postgres"
      password = random_password.gcp_postgresql_password.result
    }
  ]
  
  depends_on = [
    google_project_service.required_apis,
    google_service_networking_connection.private_vpc_connection
  ]
}

# GCP Memorystore (Redis)
module "gcp_memorystore" {
  source = "../modules/storage/gcp/memorystore"
  
  project_id = var.gcp_project_id
  region     = var.gcp_region
  
  instance_name = "redis-mlops-${local.resource_suffix}"
  
  memory_size_gb = 4
  redis_version  = "REDIS_7_0"
  
  authorized_network = module.gcp_vpc.network_id
  
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }
  
  depends_on = [google_project_service.required_apis]
}

# GCP Cloud Storage
module "gcp_storage" {
  source = "../modules/storage/gcp/storage"
  
  project_id = var.gcp_project_id
  
  buckets = [
    {
      name          = local.gcp_bucket_name
      location      = var.gcp_region
      storage_class = "STANDARD"
      
      versioning = true
      
      lifecycle_rules = [
        {
          condition = {
            age = 30
          }
          action = {
            type          = "SetStorageClass"
            storage_class = "NEARLINE"
          }
        },
        {
          condition = {
            age = 90
          }
          action = {
            type          = "SetStorageClass"
            storage_class = "COLDLINE"
          }
        },
        {
          condition = {
            age = 365
          }
          action = {
            type          = "SetStorageClass"
            storage_class = "ARCHIVE"
          }
        }
      ]
      
      uniform_bucket_level_access = true
    }
  ]
  
  depends_on = [google_project_service.required_apis]
}

# GCP Vertex AI Workbench
module "gcp_vertex_ai" {
  source = "../modules/ml/gcp"
  
  project_id = var.gcp_project_id
  region     = var.gcp_region
  
  notebook_instance = {
    name         = "mlops-workbench-${local.resource_suffix}"
    machine_type = var.gcp_machine_types.general
    
    vm_image = {
      project      = "deeplearning-platform-release"
      image_family = "tf-2-11-cpu"
    }
    
    network    = module.gcp_vpc.network_name
    subnet     = module.gcp_vpc.private_subnet_name
    
    no_public_ip = true
    
    service_account = module.gcp_security.vertex_ai_service_account_email
  }
  
  depends_on = [google_project_service.required_apis]
}

# GCP Security (IAM, Secret Manager)
module "gcp_security" {
  source = "../modules/security/gcp"
  
  project_id = var.gcp_project_id
  
  service_accounts = {
    gke = {
      account_id   = "gke-sa-${random_id.suffix.hex}"
      display_name = "GKE Service Account"
    }
    vertex_ai = {
      account_id   = "vertex-ai-sa-${random_id.suffix.hex}"
      display_name = "Vertex AI Service Account"
    }
  }
  
  secrets = {
    postgresql_password = {
      secret_id = "postgresql-password"
      data      = random_password.gcp_postgresql_password.result
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Private Service Networking for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  project       = var.gcp_project_id
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = module.gcp_vpc.network_id
  
  depends_on = [google_project_service.required_apis]
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = module.gcp_vpc.network_id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
  
  depends_on = [google_project_service.required_apis]
}

# Random password for PostgreSQL
resource "random_password" "gcp_postgresql_password" {
  length  = 16
  special = true
}
