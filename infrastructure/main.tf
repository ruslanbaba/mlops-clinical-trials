# Multi-Cloud Terraform Configuration

terraform {
  required_version = ">= 1.6.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4"
    }
  }

  # Remote state backend - configure based on your preference
  backend "s3" {
    # Configure for AWS S3 backend
    # bucket = "mlops-clinical-trials-terraform-state"
    # key    = "infrastructure/terraform.tfstate"
    # region = "us-west-2"
    # encrypt = true
    # dynamodb_table = "terraform-locks"
  }

  # Alternative: Azure backend
  # backend "azurerm" {
  #   resource_group_name  = "terraform-state-rg"
  #   storage_account_name = "mlopsstate"
  #   container_name      = "tfstate"
  #   key                 = "infrastructure.tfstate"
  # }

  # Alternative: GCS backend
  # backend "gcs" {
  #   bucket = "mlops-clinical-trials-tfstate"
  #   prefix = "infrastructure"
  # }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "mlops-clinical-trials"
      Environment = var.environment
      ManagedBy   = "terraform"
      CostCenter  = var.cost_center
    }
  }
}

# Azure Provider Configuration
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
  
  subscription_id = var.azure_subscription_id
}

# Google Cloud Provider Configuration
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# Data sources for existing resources
data "aws_availability_zones" "available" {
  state = "available"
}

data "azurerm_client_config" "current" {}

data "google_client_config" "default" {}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# Local values for common configurations
locals {
  common_tags = {
    Project     = "mlops-clinical-trials"
    Environment = var.environment
    ManagedBy   = "terraform"
    CostCenter  = var.cost_center
  }
  
  resource_suffix = "${var.environment}-${random_id.suffix.hex}"
  
  # Kubernetes cluster names
  aws_cluster_name   = "mlops-eks-${local.resource_suffix}"
  azure_cluster_name = "mlops-aks-${local.resource_suffix}"
  gcp_cluster_name   = "mlops-gke-${local.resource_suffix}"
  
  # Database names
  database_name = "mlops_clinical_trials"
  
  # Storage bucket names
  aws_bucket_name   = "mlops-data-aws-${local.resource_suffix}"
  azure_storage_name = "mlopsazure${replace(local.resource_suffix, "-", "")}"
  gcp_bucket_name   = "mlops-data-gcp-${local.resource_suffix}"
}
