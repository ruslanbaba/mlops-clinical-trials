#!/bin/bash

# Multi-Cloud MLOps Deployment Script
# This script automates the deployment of the MLOps Clinical Trials Platform
# across AWS, Azure, and GCP with multiple environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRASTRUCTURE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$INFRASTRUCTURE_DIR")"

# Default values
ENVIRONMENT=""
CLOUD_PROVIDER=""
ACTION=""
AUTO_APPROVE=false
SKIP_VALIDATION=false
PARALLEL=false

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Multi-Cloud MLOps Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -e, --environment ENVIRONMENT    Target environment (dev, staging, prod)
    -c, --cloud CLOUD               Cloud provider (aws, azure, gcp, all)
    -a, --action ACTION             Action to perform (plan, apply, destroy, validate)
    --auto-approve                  Auto-approve Terraform operations
    --skip-validation              Skip pre-deployment validation
    --parallel                     Deploy to multiple clouds in parallel
    -h, --help                     Show this help message

EXAMPLES:
    # Deploy to development environment on AWS
    $0 -e dev -c aws -a apply

    # Plan production deployment across all clouds
    $0 -e prod -c all -a plan

    # Destroy staging environment on Azure with auto-approve
    $0 -e staging -c azure -a destroy --auto-approve

    # Validate infrastructure across all clouds in parallel
    $0 -e prod -c all -a validate --parallel

ENVIRONMENTS:
    dev         Development environment with minimal resources
    staging     Staging environment with production-like configuration
    prod        Production environment with full redundancy

CLOUD PROVIDERS:
    aws         Amazon Web Services
    azure       Microsoft Azure
    gcp         Google Cloud Platform
    all         Deploy to all cloud providers

ACTIONS:
    validate    Validate Terraform configurations
    plan        Show planned infrastructure changes
    apply       Apply infrastructure changes
    destroy     Destroy infrastructure
    output      Show Terraform outputs
EOF
}

# Function to validate prerequisites
validate_prerequisites() {
    print_header "Validating Prerequisites"
    
    # Check required tools
    local tools=("terraform" "kubectl" "helm" "aws" "az" "gcloud")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            print_error "$tool is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check Terraform version
    local tf_version=$(terraform version -json | jq -r '.terraform_version')
    local min_version="1.6.0"
    if ! printf '%s\n%s\n' "$min_version" "$tf_version" | sort -V -C; then
        print_error "Terraform version $tf_version is less than required $min_version"
        exit 1
    fi
    
    # Check cloud provider authentication
    if [[ "$CLOUD_PROVIDER" == "aws" || "$CLOUD_PROVIDER" == "all" ]]; then
        if ! aws sts get-caller-identity &> /dev/null; then
            print_error "AWS authentication failed. Please configure AWS credentials."
            exit 1
        fi
    fi
    
    if [[ "$CLOUD_PROVIDER" == "azure" || "$CLOUD_PROVIDER" == "all" ]]; then
        if ! az account show &> /dev/null; then
            print_error "Azure authentication failed. Please login with 'az login'."
            exit 1
        fi
    fi
    
    if [[ "$CLOUD_PROVIDER" == "gcp" || "$CLOUD_PROVIDER" == "all" ]]; then
        if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
            print_error "GCP authentication failed. Please authenticate with 'gcloud auth login'."
            exit 1
        fi
    fi
    
    print_status "Prerequisites validation completed successfully"
}

# Function to initialize Terraform backend
init_terraform() {
    local env_dir="$1"
    local cloud="$2"
    
    print_status "Initializing Terraform for $cloud in $ENVIRONMENT environment"
    
    cd "$env_dir"
    
    # Initialize Terraform
    if ! terraform init -upgrade; then
        print_error "Failed to initialize Terraform for $cloud"
        return 1
    fi
    
    # Validate configuration
    if ! terraform validate; then
        print_error "Terraform validation failed for $cloud"
        return 1
    fi
    
    print_status "Terraform initialized successfully for $cloud"
}

# Function to run Terraform plan
terraform_plan() {
    local env_dir="$1"
    local cloud="$2"
    
    print_status "Planning Terraform deployment for $cloud"
    
    cd "$env_dir"
    
    local plan_file="tfplan-$cloud-$(date +%Y%m%d-%H%M%S)"
    
    if terraform plan -out="$plan_file" -var-file="../../environments/$ENVIRONMENT/terraform.tfvars"; then
        print_status "Terraform plan completed successfully for $cloud"
        echo "Plan file: $plan_file"
    else
        print_error "Terraform plan failed for $cloud"
        return 1
    fi
}

# Function to run Terraform apply
terraform_apply() {
    local env_dir="$1"
    local cloud="$2"
    
    print_status "Applying Terraform configuration for $cloud"
    
    cd "$env_dir"
    
    local apply_args=""
    if [[ "$AUTO_APPROVE" == "true" ]]; then
        apply_args="-auto-approve"
    fi
    
    if terraform apply $apply_args -var-file="../../environments/$ENVIRONMENT/terraform.tfvars"; then
        print_status "Terraform apply completed successfully for $cloud"
    else
        print_error "Terraform apply failed for $cloud"
        return 1
    fi
}

# Function to run Terraform destroy
terraform_destroy() {
    local env_dir="$1"
    local cloud="$2"
    
    print_warning "Destroying infrastructure for $cloud in $ENVIRONMENT environment"
    
    if [[ "$AUTO_APPROVE" != "true" ]]; then
        read -p "Are you sure you want to destroy the infrastructure? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            print_status "Destroy operation cancelled"
            return 0
        fi
    fi
    
    cd "$env_dir"
    
    local destroy_args=""
    if [[ "$AUTO_APPROVE" == "true" ]]; then
        destroy_args="-auto-approve"
    fi
    
    if terraform destroy $destroy_args -var-file="../../environments/$ENVIRONMENT/terraform.tfvars"; then
        print_status "Infrastructure destroyed successfully for $cloud"
    else
        print_error "Failed to destroy infrastructure for $cloud"
        return 1
    fi
}

# Function to show Terraform outputs
terraform_output() {
    local env_dir="$1"
    local cloud="$2"
    
    print_status "Showing Terraform outputs for $cloud"
    
    cd "$env_dir"
    
    terraform output -json | jq .
}

# Function to deploy to a specific cloud
deploy_cloud() {
    local cloud="$1"
    
    print_header "Processing $cloud deployment"
    
    local env_dir="$INFRASTRUCTURE_DIR/environments/$ENVIRONMENT"
    
    # Check if environment directory exists
    if [[ ! -d "$env_dir" ]]; then
        print_error "Environment directory not found: $env_dir"
        return 1
    fi
    
    # Initialize Terraform
    if ! init_terraform "$env_dir" "$cloud"; then
        return 1
    fi
    
    # Execute the requested action
    case "$ACTION" in
        "validate")
            print_status "Validation completed for $cloud"
            ;;
        "plan")
            terraform_plan "$env_dir" "$cloud"
            ;;
        "apply")
            terraform_apply "$env_dir" "$cloud"
            ;;
        "destroy")
            terraform_destroy "$env_dir" "$cloud"
            ;;
        "output")
            terraform_output "$env_dir" "$cloud"
            ;;
        *)
            print_error "Unknown action: $ACTION"
            return 1
            ;;
    esac
}

# Function to deploy in parallel
deploy_parallel() {
    local clouds=("$@")
    local pids=()
    
    print_header "Starting parallel deployment to ${clouds[*]}"
    
    # Start background processes
    for cloud in "${clouds[@]}"; do
        deploy_cloud "$cloud" &
        pids+=($!)
        print_status "Started deployment for $cloud (PID: ${pids[-1]})"
    done
    
    # Wait for all processes to complete
    local exit_code=0
    for i in "${!pids[@]}"; do
        if ! wait "${pids[$i]}"; then
            print_error "Deployment failed for ${clouds[$i]}"
            exit_code=1
        fi
    done
    
    return $exit_code
}

# Function to configure kubectl contexts
configure_kubectl() {
    print_header "Configuring kubectl contexts"
    
    case "$CLOUD_PROVIDER" in
        "aws"|"all")
            # Configure AWS EKS
            local aws_cluster_name=$(terraform -chdir="$INFRASTRUCTURE_DIR/environments/$ENVIRONMENT" output -json | jq -r '.aws_cluster_name.value // empty')
            if [[ -n "$aws_cluster_name" ]]; then
                aws eks update-kubeconfig --name "$aws_cluster_name" --region us-west-2
                kubectl config rename-context "arn:aws:eks:us-west-2:*:cluster/$aws_cluster_name" "aws-$ENVIRONMENT"
            fi
            ;;
    esac
    
    case "$CLOUD_PROVIDER" in
        "azure"|"all")
            # Configure Azure AKS
            local azure_cluster_name=$(terraform -chdir="$INFRASTRUCTURE_DIR/environments/$ENVIRONMENT" output -json | jq -r '.azure_cluster_name.value // empty')
            local azure_resource_group=$(terraform -chdir="$INFRASTRUCTURE_DIR/environments/$ENVIRONMENT" output -json | jq -r '.azure_resource_group.value // empty')
            if [[ -n "$azure_cluster_name" && -n "$azure_resource_group" ]]; then
                az aks get-credentials --name "$azure_cluster_name" --resource-group "$azure_resource_group"
                kubectl config rename-context "$azure_cluster_name" "azure-$ENVIRONMENT"
            fi
            ;;
    esac
    
    case "$CLOUD_PROVIDER" in
        "gcp"|"all")
            # Configure GCP GKE
            local gcp_cluster_name=$(terraform -chdir="$INFRASTRUCTURE_DIR/environments/$ENVIRONMENT" output -json | jq -r '.gcp_cluster_name.value // empty')
            local gcp_project_id=$(terraform -chdir="$INFRASTRUCTURE_DIR/environments/$ENVIRONMENT" output -json | jq -r '.gcp_project_id.value // empty')
            if [[ -n "$gcp_cluster_name" && -n "$gcp_project_id" ]]; then
                gcloud container clusters get-credentials "$gcp_cluster_name" --region us-central1 --project "$gcp_project_id"
                kubectl config rename-context "gke_${gcp_project_id}_us-central1_${gcp_cluster_name}" "gcp-$ENVIRONMENT"
            fi
            ;;
    esac
    
    print_status "kubectl contexts configured successfully"
}

# Main execution function
main() {
    print_header "MLOps Clinical Trials Platform - Multi-Cloud Deployment"
    
    # Validate inputs
    if [[ -z "$ENVIRONMENT" || -z "$CLOUD_PROVIDER" || -z "$ACTION" ]]; then
        print_error "Missing required parameters"
        show_usage
        exit 1
    fi
    
    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
        print_error "Invalid environment: $ENVIRONMENT"
        exit 1
    fi
    
    # Validate cloud provider
    if [[ ! "$CLOUD_PROVIDER" =~ ^(aws|azure|gcp|all)$ ]]; then
        print_error "Invalid cloud provider: $CLOUD_PROVIDER"
        exit 1
    fi
    
    # Validate action
    if [[ ! "$ACTION" =~ ^(validate|plan|apply|destroy|output)$ ]]; then
        print_error "Invalid action: $ACTION"
        exit 1
    fi
    
    # Run prerequisites validation
    if [[ "$SKIP_VALIDATION" != "true" ]]; then
        validate_prerequisites
    fi
    
    # Determine clouds to deploy
    local clouds=()
    if [[ "$CLOUD_PROVIDER" == "all" ]]; then
        clouds=("aws" "azure" "gcp")
    else
        clouds=("$CLOUD_PROVIDER")
    fi
    
    # Execute deployment
    if [[ "$PARALLEL" == "true" && ${#clouds[@]} -gt 1 ]]; then
        deploy_parallel "${clouds[@]}"
    else
        for cloud in "${clouds[@]}"; do
            deploy_cloud "$cloud"
        done
    fi
    
    # Configure kubectl if apply was successful
    if [[ "$ACTION" == "apply" ]]; then
        configure_kubectl
    fi
    
    print_header "Deployment completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -c|--cloud)
            CLOUD_PROVIDER="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        --auto-approve)
            AUTO_APPROVE=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Execute main function
main
