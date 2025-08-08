"""
Database initialization script for the clinical trials platform.
"""

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config import config
from logger import get_logger

logger = get_logger(__name__)


def create_database():
    """Create the main database if it doesn't exist."""
    try:
        # Connect to PostgreSQL server (not specific database)
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="clinical_user",
            password="clinical_password",
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'clinical_trials'")
        exists = cursor.fetchone()
        
        if not exists:
            logger.info("Creating clinical_trials database...")
            cursor.execute("CREATE DATABASE clinical_trials")
            logger.info("Database created successfully")
        else:
            logger.info("Database already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to create database: {str(e)}")
        raise


def create_tables():
    """Create necessary tables for the clinical trials platform."""
    
    # SQL for creating tables
    create_tables_sql = """
    -- Patients table
    CREATE TABLE IF NOT EXISTS patients (
        patient_id VARCHAR(20) PRIMARY KEY,
        age INTEGER NOT NULL CHECK (age >= 18 AND age <= 120),
        gender VARCHAR(10) NOT NULL CHECK (gender IN ('M', 'F', 'Other')),
        race VARCHAR(50),
        ethnicity VARCHAR(50),
        income_level VARCHAR(20),
        education_level VARCHAR(50),
        zip_code VARCHAR(10),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Clinical trials table
    CREATE TABLE IF NOT EXISTS clinical_trials (
        trial_id VARCHAR(20) PRIMARY KEY,
        trial_name VARCHAR(255) NOT NULL,
        cancer_type VARCHAR(100) NOT NULL,
        phase VARCHAR(10) CHECK (phase IN ('I', 'II', 'III', 'IV')),
        status VARCHAR(20) DEFAULT 'Active',
        start_date DATE,
        end_date DATE,
        principal_investigator VARCHAR(255),
        institution VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Patient enrollment table
    CREATE TABLE IF NOT EXISTS patient_enrollment (
        enrollment_id SERIAL PRIMARY KEY,
        patient_id VARCHAR(20) REFERENCES patients(patient_id),
        trial_id VARCHAR(20) REFERENCES clinical_trials(trial_id),
        enrollment_date DATE NOT NULL,
        status VARCHAR(20) DEFAULT 'Enrolled',
        randomization_arm VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(patient_id, trial_id)
    );

    -- Clinical measurements table
    CREATE TABLE IF NOT EXISTS clinical_measurements (
        measurement_id SERIAL PRIMARY KEY,
        patient_id VARCHAR(20) REFERENCES patients(patient_id),
        measurement_date DATE NOT NULL,
        measurement_type VARCHAR(100) NOT NULL,
        value DECIMAL(10,4),
        unit VARCHAR(20),
        normal_range_min DECIMAL(10,4),
        normal_range_max DECIMAL(10,4),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Tumor characteristics table
    CREATE TABLE IF NOT EXISTS tumor_characteristics (
        tumor_id SERIAL PRIMARY KEY,
        patient_id VARCHAR(20) REFERENCES patients(patient_id),
        diagnosis_date DATE NOT NULL,
        cancer_type VARCHAR(100) NOT NULL,
        tumor_size DECIMAL(5,2),
        grade INTEGER CHECK (grade IN (1, 2, 3, 4)),
        stage VARCHAR(10),
        histology_type VARCHAR(100),
        lymph_nodes_positive INTEGER DEFAULT 0,
        metastasis_present BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Biomarkers table
    CREATE TABLE IF NOT EXISTS biomarkers (
        biomarker_id SERIAL PRIMARY KEY,
        patient_id VARCHAR(20) REFERENCES patients(patient_id),
        test_date DATE NOT NULL,
        biomarker_name VARCHAR(100) NOT NULL,
        value DECIMAL(10,4),
        status VARCHAR(20),
        method VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Treatments table
    CREATE TABLE IF NOT EXISTS treatments (
        treatment_id SERIAL PRIMARY KEY,
        patient_id VARCHAR(20) REFERENCES patients(patient_id),
        trial_id VARCHAR(20) REFERENCES clinical_trials(trial_id),
        treatment_type VARCHAR(100) NOT NULL,
        drug_name VARCHAR(255),
        dosage VARCHAR(100),
        frequency VARCHAR(100),
        start_date DATE NOT NULL,
        end_date DATE,
        response VARCHAR(50),
        side_effects TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Outcomes table
    CREATE TABLE IF NOT EXISTS outcomes (
        outcome_id SERIAL PRIMARY KEY,
        patient_id VARCHAR(20) REFERENCES patients(patient_id),
        trial_id VARCHAR(20) REFERENCES clinical_trials(trial_id),
        outcome_type VARCHAR(100) NOT NULL,
        outcome_date DATE NOT NULL,
        value VARCHAR(255),
        survival_months INTEGER,
        progression_free_survival_months INTEGER,
        response_type VARCHAR(50),
        quality_of_life_score INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Model predictions table
    CREATE TABLE IF NOT EXISTS model_predictions (
        prediction_id SERIAL PRIMARY KEY,
        patient_id VARCHAR(20) REFERENCES patients(patient_id),
        model_name VARCHAR(100) NOT NULL,
        model_version VARCHAR(50) NOT NULL,
        prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        prediction_value DECIMAL(5,4),
        prediction_class VARCHAR(50),
        confidence_score DECIMAL(5,4),
        feature_values JSONB,
        ab_test_id VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Model performance metrics table
    CREATE TABLE IF NOT EXISTS model_metrics (
        metric_id SERIAL PRIMARY KEY,
        model_name VARCHAR(100) NOT NULL,
        model_version VARCHAR(50) NOT NULL,
        metric_name VARCHAR(100) NOT NULL,
        metric_value DECIMAL(10,6),
        dataset_type VARCHAR(20),
        calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- A/B test results table
    CREATE TABLE IF NOT EXISTS ab_test_results (
        result_id SERIAL PRIMARY KEY,
        test_id VARCHAR(100) NOT NULL,
        model_version VARCHAR(50) NOT NULL,
        prediction_id INTEGER REFERENCES model_predictions(prediction_id),
        response_time_ms INTEGER,
        success BOOLEAN DEFAULT TRUE,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Data quality metrics table
    CREATE TABLE IF NOT EXISTS data_quality_metrics (
        quality_id SERIAL PRIMARY KEY,
        table_name VARCHAR(100) NOT NULL,
        column_name VARCHAR(100),
        metric_name VARCHAR(100) NOT NULL,
        metric_value DECIMAL(10,6),
        check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Audit log table
    CREATE TABLE IF NOT EXISTS audit_log (
        log_id SERIAL PRIMARY KEY,
        user_id VARCHAR(100),
        action VARCHAR(100) NOT NULL,
        table_name VARCHAR(100),
        record_id VARCHAR(100),
        old_values JSONB,
        new_values JSONB,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address INET,
        user_agent TEXT
    );

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_patients_age ON patients(age);
    CREATE INDEX IF NOT EXISTS idx_patients_gender ON patients(gender);
    CREATE INDEX IF NOT EXISTS idx_clinical_measurements_patient_date ON clinical_measurements(patient_id, measurement_date);
    CREATE INDEX IF NOT EXISTS idx_tumor_characteristics_patient ON tumor_characteristics(patient_id);
    CREATE INDEX IF NOT EXISTS idx_biomarkers_patient_date ON biomarkers(patient_id, test_date);
    CREATE INDEX IF NOT EXISTS idx_treatments_patient ON treatments(patient_id);
    CREATE INDEX IF NOT EXISTS idx_outcomes_patient ON outcomes(patient_id);
    CREATE INDEX IF NOT EXISTS idx_model_predictions_patient ON model_predictions(patient_id);
    CREATE INDEX IF NOT EXISTS idx_model_predictions_model ON model_predictions(model_name, model_version);
    CREATE INDEX IF NOT EXISTS idx_ab_test_results_test_id ON ab_test_results(test_id);
    
    -- Create functions for updated_at timestamps
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    -- Create triggers for updated_at
    CREATE TRIGGER update_patients_updated_at BEFORE UPDATE ON patients
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    CREATE TRIGGER update_clinical_trials_updated_at BEFORE UPDATE ON clinical_trials
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
    
    try:
        # Connect to the clinical_trials database
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="clinical_user",
            password="clinical_password",
            database="clinical_trials"
        )
        
        cursor = conn.cursor()
        
        logger.info("Creating tables...")
        cursor.execute(create_tables_sql)
        conn.commit()
        
        logger.info("Tables created successfully")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to create tables: {str(e)}")
        raise


def insert_sample_data():
    """Insert sample data for testing."""
    
    sample_data_sql = """
    -- Insert sample patients
    INSERT INTO patients (patient_id, age, gender, race, ethnicity, income_level, education_level, zip_code)
    VALUES 
        ('PAT-00000001', 45, 'F', 'White', 'Non-Hispanic', 'Middle', 'Bachelor', '12345'),
        ('PAT-00000002', 62, 'M', 'Black', 'Non-Hispanic', 'Low', 'High School', '12346'),
        ('PAT-00000003', 38, 'F', 'Asian', 'Non-Hispanic', 'High', 'Graduate', '12347'),
        ('PAT-00000004', 55, 'M', 'White', 'Hispanic', 'Middle', 'Bachelor', '12348'),
        ('PAT-00000005', 41, 'F', 'Other', 'Non-Hispanic', 'Low', 'Some College', '12349')
    ON CONFLICT (patient_id) DO NOTHING;

    -- Insert sample clinical trials
    INSERT INTO clinical_trials (trial_id, trial_name, cancer_type, phase, status, start_date, principal_investigator, institution)
    VALUES 
        ('TRIAL-001', 'Breast Cancer Immunotherapy Study', 'Breast Cancer', 'II', 'Active', '2023-01-01', 'Dr. Smith', 'City Hospital'),
        ('TRIAL-002', 'Lung Cancer Targeted Therapy', 'Lung Cancer', 'III', 'Active', '2023-02-01', 'Dr. Johnson', 'University Medical Center'),
        ('TRIAL-003', 'Prostate Cancer Prevention Study', 'Prostate Cancer', 'I', 'Recruiting', '2023-03-01', 'Dr. Brown', 'Cancer Institute')
    ON CONFLICT (trial_id) DO NOTHING;

    -- Insert sample tumor characteristics
    INSERT INTO tumor_characteristics (patient_id, diagnosis_date, cancer_type, tumor_size, grade, stage, histology_type, lymph_nodes_positive)
    VALUES 
        ('PAT-00000001', '2023-01-15', 'Breast Cancer', 2.5, 2, 'IIA', 'Invasive Ductal Carcinoma', 1),
        ('PAT-00000002', '2023-02-10', 'Lung Cancer', 4.2, 3, 'IIIA', 'Adenocarcinoma', 3),
        ('PAT-00000003', '2023-01-20', 'Breast Cancer', 1.8, 1, 'IA', 'Invasive Lobular Carcinoma', 0),
        ('PAT-00000004', '2023-03-05', 'Prostate Cancer', 3.1, 2, 'T2', 'Adenocarcinoma', 0),
        ('PAT-00000005', '2023-02-20', 'Breast Cancer', 3.5, 3, 'IIB', 'Invasive Ductal Carcinoma', 2)
    ON CONFLICT DO NOTHING;

    -- Insert sample biomarkers
    INSERT INTO biomarkers (patient_id, test_date, biomarker_name, value, status, method)
    VALUES 
        ('PAT-00000001', '2023-01-16', 'ER', 85.0, 'Positive', 'IHC'),
        ('PAT-00000001', '2023-01-16', 'PR', 70.0, 'Positive', 'IHC'),
        ('PAT-00000001', '2023-01-16', 'HER2', 1.0, 'Negative', 'IHC'),
        ('PAT-00000002', '2023-02-11', 'EGFR', NULL, 'Negative', 'PCR'),
        ('PAT-00000003', '2023-01-21', 'ER', 95.0, 'Positive', 'IHC'),
        ('PAT-00000004', '2023-03-06', 'PSA', 8.5, 'Elevated', 'Blood Test')
    ON CONFLICT DO NOTHING;
    """
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="clinical_user",
            password="clinical_password",
            database="clinical_trials"
        )
        
        cursor = conn.cursor()
        
        logger.info("Inserting sample data...")
        cursor.execute(sample_data_sql)
        conn.commit()
        
        logger.info("Sample data inserted successfully")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to insert sample data: {str(e)}")
        raise


def main():
    """Main function to initialize the database."""
    logger.info("Starting database initialization...")
    
    try:
        # Create database
        create_database()
        
        # Create tables
        create_tables()
        
        # Insert sample data
        insert_sample_data()
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
