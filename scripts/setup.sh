#!/bin/bash

# MLOps Clinical Trials Platform Setup Script
# This script sets up the complete MLOps platform for clinical trial analytics

set -e  # Exit on any error

echo "🚀 Starting MLOps Clinical Trials Platform Setup..."
echo "=================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    print_header "Checking requirements..."
    
    local required_tools=("docker" "docker-compose" "kubectl" "python3" "pip")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command -v $tool &> /dev/null; then
            missing_tools+=($tool)
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install the missing tools and run this script again."
        exit 1
    fi
    
    print_status "All required tools are installed."
}

# Set up Python environment
setup_python_env() {
    print_header "Setting up Python environment..."
    
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    
    print_status "Installing pre-commit hooks..."
    pre-commit install
    
    print_status "Python environment setup complete."
}

# Create necessary directories
create_directories() {
    print_header "Creating necessary directories..."
    
    local directories=(
        "data/raw"
        "data/processed"
        "data/features"
        "models"
        "logs"
        "mlruns"
        "monitoring/grafana/dashboards"
        "monitoring/grafana/datasources"
        "tests/unit"
        "tests/integration"
        "docs"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    done
}

# Initialize database
init_database() {
    print_header "Initializing database..."
    
    print_status "Starting PostgreSQL container..."
    docker-compose up -d postgres
    
    print_status "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    print_status "Running database initialization script..."
    python scripts/init_database.py
    
    print_status "Database initialization complete."
}

# Setup MLflow
setup_mlflow() {
    print_header "Setting up MLflow..."
    
    print_status "Starting MLflow dependencies..."
    docker-compose up -d postgres minio
    
    print_status "Waiting for services to be ready..."
    sleep 15
    
    print_status "Starting MLflow tracking server..."
    docker-compose up -d mlflow
    
    print_status "Waiting for MLflow to be ready..."
    sleep 10
    
    print_status "MLflow setup complete. Access at http://localhost:5000"
}

# Setup monitoring
setup_monitoring() {
    print_header "Setting up monitoring..."
    
    print_status "Creating Prometheus configuration..."
    cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'model-serving'
    static_configs:
      - targets: ['model-serving-baseline:8080', 'model-serving-candidate:8080']
    metrics_path: '/metrics'

  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:8080']
    metrics_path: '/metrics'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
EOF

    print_status "Creating Grafana datasource configuration..."
    mkdir -p monitoring/grafana/datasources
    cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    print_status "Starting monitoring services..."
    docker-compose up -d prometheus grafana
    
    print_status "Monitoring setup complete."
    print_status "Grafana: http://localhost:3000 (admin/grafana_password)"
    print_status "Prometheus: http://localhost:9090"
}

# Setup Kubernetes (optional)
setup_kubernetes() {
    print_header "Setting up Kubernetes deployment..."
    
    if ! command -v kubectl &> /dev/null; then
        print_warning "kubectl not found. Skipping Kubernetes setup."
        return
    fi
    
    print_status "Creating namespace..."
    kubectl create namespace clinical-trials --dry-run=client -o yaml | kubectl apply -f -
    
    print_status "Applying Kubernetes manifests..."
    kubectl apply -f deployments/model-serving/
    
    print_status "Setting up Istio (if available)..."
    if command -v istioctl &> /dev/null; then
        kubectl apply -f deployments/istio/
        print_status "Istio configuration applied."
    else
        print_warning "Istio not found. Skipping Istio setup."
    fi
    
    print_status "Kubernetes setup complete."
}

# Generate sample data
generate_sample_data() {
    print_header "Generating sample data..."
    
    if [ -f "scripts/generate_test_data.py" ]; then
        print_status "Generating synthetic clinical trial data..."
        python scripts/generate_test_data.py --samples 10000 --output data/raw/
        print_status "Sample data generated."
    else
        print_warning "Sample data generation script not found. Skipping."
    fi
}

# Run initial model training
train_initial_model() {
    print_header "Training initial model..."
    
    if [ -f "data/raw/breast_cancer.csv" ]; then
        print_status "Training breast cancer risk assessment model..."
        python src/training/train_model.py --config configs/breast_cancer.yaml
        print_status "Initial model training complete."
    else
        print_warning "Training data not found. Skipping initial model training."
    fi
}

# Start all services
start_services() {
    print_header "Starting all services..."
    
    print_status "Starting Docker Compose services..."
    docker-compose up -d
    
    print_status "Waiting for services to be ready..."
    sleep 30
    
    print_status "All services started successfully!"
    
    echo ""
    echo "🎉 MLOps Clinical Trials Platform Setup Complete!"
    echo "=================================================="
    echo ""
    echo "📊 Service URLs:"
    echo "   • API Gateway:     http://localhost:8000"
    echo "   • MLflow:          http://localhost:5000"
    echo "   • Grafana:         http://localhost:3000 (admin/grafana_password)"
    echo "   • Prometheus:      http://localhost:9090"
    echo "   • Jupyter Lab:     http://localhost:8888"
    echo "   • MinIO Console:   http://localhost:9001 (minioadmin/minioadmin123)"
    echo ""
    echo "🔍 Health Checks:"
    echo "   • API Health:      curl http://localhost:8000/health"
    echo "   • Model Health:    curl http://localhost:8080/health"
    echo ""
    echo "📚 Next Steps:"
    echo "   1. Access Jupyter Lab to explore the notebooks"
    echo "   2. Check Grafana dashboards for monitoring"
    echo "   3. Train your first model: make train-model"
    echo "   4. Deploy model: make deploy-local"
    echo ""
}

# Cleanup function
cleanup() {
    print_header "Cleaning up..."
    docker-compose down
    print_status "Cleanup complete."
}

# Handle script interruption
trap cleanup EXIT

# Main execution flow
main() {
    case "${1:-all}" in
        "requirements")
            check_requirements
            ;;
        "python")
            setup_python_env
            ;;
        "directories")
            create_directories
            ;;
        "database")
            init_database
            ;;
        "mlflow")
            setup_mlflow
            ;;
        "monitoring")
            setup_monitoring
            ;;
        "kubernetes")
            setup_kubernetes
            ;;
        "data")
            generate_sample_data
            ;;
        "train")
            train_initial_model
            ;;
        "services")
            start_services
            ;;
        "all")
            check_requirements
            setup_python_env
            create_directories
            init_database
            setup_mlflow
            setup_monitoring
            generate_sample_data
            train_initial_model
            start_services
            ;;
        "help")
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  requirements  - Check system requirements"
            echo "  python        - Setup Python environment"
            echo "  directories   - Create necessary directories"
            echo "  database      - Initialize database"
            echo "  mlflow        - Setup MLflow"
            echo "  monitoring    - Setup monitoring"
            echo "  kubernetes    - Setup Kubernetes"
            echo "  data          - Generate sample data"
            echo "  train         - Train initial model"
            echo "  services      - Start all services"
            echo "  all           - Run complete setup (default)"
            echo "  help          - Show this help message"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Use '$0 help' for usage information."
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
