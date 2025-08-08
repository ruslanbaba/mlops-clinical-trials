# Load Testing Configuration for Traffic Surge Validation
# k6 scripts for testing API endpoints and validating auto-scaling behavior

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const predictionLatency = new Trend('prediction_latency');
const throughput = new Rate('throughput');

// Test configuration
export const options = {
  scenarios: {
    // Baseline load test
    baseline_load: {
      executor: 'constant-vus',
      vus: 10,
      duration: '2m',
      tags: { test_type: 'baseline' },
    },
    
    // Gradual ramp-up to test auto-scaling
    ramp_up_test: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '1m', target: 50 },   // Ramp up to 50 users
        { duration: '2m', target: 100 },  // Ramp up to 100 users
        { duration: '2m', target: 200 },  // Ramp up to 200 users
        { duration: '3m', target: 200 },  // Stay at 200 users
        { duration: '1m', target: 0 },    // Ramp down
      ],
      tags: { test_type: 'ramp_up' },
    },
    
    // Spike test to validate surge handling
    spike_test: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '30s', target: 10 },   // Normal load
        { duration: '30s', target: 500 },  // Sudden spike
        { duration: '2m', target: 500 },   // Maintain spike
        { duration: '30s', target: 10 },   // Back to normal
      ],
      tags: { test_type: 'spike' },
      startTime: '5m',  // Start after ramp-up test
    },
    
    // Stress test to find breaking point
    stress_test: {
      executor: 'ramping-vus',
      startVUs: 50,
      stages: [
        { duration: '1m', target: 100 },
        { duration: '1m', target: 200 },
        { duration: '1m', target: 400 },
        { duration: '1m', target: 800 },
        { duration: '2m', target: 800 },
        { duration: '1m', target: 0 },
      ],
      tags: { test_type: 'stress' },
      startTime: '10m',
    },
    
    // Endurance test
    endurance_test: {
      executor: 'constant-vus',
      vus: 100,
      duration: '10m',
      tags: { test_type: 'endurance' },
      startTime: '15m',
    },
  },
  
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests under 2s
    http_req_failed: ['rate<0.1'],     // Less than 10% errors
    errors: ['rate<0.05'],             // Less than 5% application errors
    prediction_latency: ['p(95)<3000'], // Model predictions under 3s
    throughput: ['rate>10'],           // At least 10 req/s throughput
  },
};

// Environment variables
const BASE_URL = __ENV.ENDPOINT || 'https://api.mlops-clinical-trials.com';
const API_KEY = __ENV.API_KEY || 'test-api-key';

// Test data
const testPatients = [
  {
    age: 65,
    gender: 'M',
    stage: 'III',
    histology: 'adenocarcinoma',
    smoking_history: 'former',
    performance_status: 1,
    biomarkers: {
      egfr: 'negative',
      alk: 'negative',
      pd_l1: 45
    }
  },
  {
    age: 58,
    gender: 'F',
    stage: 'II',
    histology: 'squamous',
    smoking_history: 'never',
    performance_status: 0,
    biomarkers: {
      egfr: 'positive',
      alk: 'negative',
      pd_l1: 80
    }
  },
  {
    age: 72,
    gender: 'M',
    stage: 'IV',
    histology: 'adenocarcinoma',
    smoking_history: 'current',
    performance_status: 2,
    biomarkers: {
      egfr: 'negative',
      alk: 'positive',
      pd_l1: 15
    }
  }
];

export default function () {
  const testType = __VU % 3; // Rotate between different test scenarios
  
  switch (testType) {
    case 0:
      testHealthEndpoint();
      break;
    case 1:
      testPredictionEndpoint();
      break;
    case 2:
      testBatchPredictionEndpoint();
      break;
  }
  
  sleep(Math.random() * 2 + 1); // Random sleep between 1-3 seconds
}

function testHealthEndpoint() {
  const response = http.get(`${BASE_URL}/health`, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'health' },
  });
  
  check(response, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 500ms': (r) => r.timings.duration < 500,
    'health check has status field': (r) => JSON.parse(r.body).status !== undefined,
  });
  
  errorRate.add(response.status >= 400);
}

function testPredictionEndpoint() {
  const patient = testPatients[Math.floor(Math.random() * testPatients.length)];
  
  const payload = JSON.stringify({
    patient_data: patient,
    model_version: 'v1.2.0',
    return_confidence: true,
    return_explanation: true
  });
  
  const startTime = Date.now();
  
  const response = http.post(`${BASE_URL}/api/v1/predict`, payload, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'predict' },
  });
  
  const endTime = Date.now();
  predictionLatency.add(endTime - startTime);
  
  const responseBody = JSON.parse(response.body || '{}');
  
  check(response, {
    'prediction status is 200': (r) => r.status === 200,
    'prediction has prediction field': (r) => responseBody.prediction !== undefined,
    'prediction has confidence field': (r) => responseBody.confidence !== undefined,
    'prediction confidence is valid': (r) => {
      const conf = responseBody.confidence;
      return conf >= 0 && conf <= 1;
    },
    'prediction response time < 2s': (r) => r.timings.duration < 2000,
  });
  
  // Check for specific model response structure
  if (response.status === 200) {
    check(responseBody, {
      'has valid prediction': (body) => ['low_risk', 'medium_risk', 'high_risk'].includes(body.prediction),
      'has model metadata': (body) => body.model_version !== undefined,
      'has explanation': (body) => body.explanation !== undefined,
    });
    
    throughput.add(1);
  } else {
    console.error(`Prediction failed: ${response.status} - ${response.body}`);
  }
  
  errorRate.add(response.status >= 400);
}

function testBatchPredictionEndpoint() {
  const batchSize = Math.floor(Math.random() * 5) + 1; // 1-5 patients
  const batch = [];
  
  for (let i = 0; i < batchSize; i++) {
    batch.push(testPatients[Math.floor(Math.random() * testPatients.length)]);
  }
  
  const payload = JSON.stringify({
    patients: batch,
    model_version: 'v1.2.0',
    return_confidence: true
  });
  
  const response = http.post(`${BASE_URL}/api/v1/predict/batch`, payload, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'batch_predict' },
    timeout: '30s',
  });
  
  const responseBody = JSON.parse(response.body || '{}');
  
  check(response, {
    'batch prediction status is 200': (r) => r.status === 200,
    'batch prediction has results': (r) => responseBody.results !== undefined,
    'batch prediction correct count': (r) => responseBody.results.length === batchSize,
    'batch prediction response time < 10s': (r) => r.timings.duration < 10000,
  });
  
  errorRate.add(response.status >= 400);
  throughput.add(batchSize);
}

export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    test_duration: data.metrics.iteration_duration.values.avg,
    scenarios: {},
    performance_metrics: {
      avg_response_time: data.metrics.http_req_duration.values.avg,
      p95_response_time: data.metrics.http_req_duration.values['p(95)'],
      p99_response_time: data.metrics.http_req_duration.values['p(99)'],
      error_rate: data.metrics.http_req_failed.values.rate,
      total_requests: data.metrics.http_reqs.values.count,
      requests_per_second: data.metrics.http_reqs.values.rate,
    },
    custom_metrics: {
      prediction_latency_p95: data.metrics.prediction_latency?.values['p(95)'] || 0,
      application_error_rate: data.metrics.errors?.values.rate || 0,
      throughput: data.metrics.throughput?.values.rate || 0,
    }
  };
  
  // Extract scenario-specific data
  Object.keys(data.metrics).forEach(metric => {
    if (metric.includes('scenario_')) {
      const scenarioName = metric.split('scenario_')[1];
      if (!summary.scenarios[scenarioName]) {
        summary.scenarios[scenarioName] = {};
      }
      summary.scenarios[scenarioName][metric] = data.metrics[metric].values;
    }
  });
  
  return {
    'load-test-summary.json': JSON.stringify(summary, null, 2),
    stdout: generateTextReport(summary),
  };
}

function generateTextReport(summary) {
  return `
=== MLOps Clinical Trials Load Test Summary ===

Test Duration: ${summary.test_duration.toFixed(2)}ms
Total Requests: ${summary.performance_metrics.total_requests}
Requests/sec: ${summary.performance_metrics.requests_per_second.toFixed(2)}

Performance Metrics:
- Average Response Time: ${summary.performance_metrics.avg_response_time.toFixed(2)}ms
- 95th Percentile: ${summary.performance_metrics.p95_response_time.toFixed(2)}ms
- 99th Percentile: ${summary.performance_metrics.p99_response_time.toFixed(2)}ms
- Error Rate: ${(summary.performance_metrics.error_rate * 100).toFixed(2)}%

Custom Metrics:
- Prediction Latency (P95): ${summary.custom_metrics.prediction_latency_p95.toFixed(2)}ms
- Application Error Rate: ${(summary.custom_metrics.application_error_rate * 100).toFixed(2)}%
- Throughput: ${summary.custom_metrics.throughput.toFixed(2)} predictions/sec

Auto-scaling Validation:
${summary.performance_metrics.p95_response_time < 2000 ? '✅' : '❌'} Response times within SLA
${summary.performance_metrics.error_rate < 0.1 ? '✅' : '❌'} Error rate below threshold
${summary.custom_metrics.throughput > 10 ? '✅' : '❌'} Throughput meets minimum requirements

=================================================
  `;
}

// Spike test specific configuration
export const spikeTestOptions = {
  scenarios: {
    spike: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '1m', target: 10 },    // Normal load
        { duration: '10s', target: 1000 }, // Sudden massive spike
        { duration: '2m', target: 1000 },  // Maintain spike
        { duration: '10s', target: 10 },   // Quick ramp down
        { duration: '1m', target: 10 },    // Recovery period
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<5000'], // More lenient during spike
    http_req_failed: ['rate<0.2'],     // Allow higher error rate during spike
  },
};

// Performance regression test
export function performanceRegressionTest() {
  const baseline = {
    avg_response_time: 500,  // ms
    p95_response_time: 1000, // ms
    error_rate: 0.05,        // 5%
    throughput: 50,          // req/sec
  };
  
  // Run current test and compare with baseline
  const current = getCurrentMetrics();
  
  const regressions = [];
  
  if (current.avg_response_time > baseline.avg_response_time * 1.2) {
    regressions.push('Average response time increased by >20%');
  }
  
  if (current.p95_response_time > baseline.p95_response_time * 1.3) {
    regressions.push('95th percentile response time increased by >30%');
  }
  
  if (current.error_rate > baseline.error_rate * 2) {
    regressions.push('Error rate doubled');
  }
  
  if (current.throughput < baseline.throughput * 0.8) {
    regressions.push('Throughput decreased by >20%');
  }
  
  return {
    passed: regressions.length === 0,
    regressions: regressions,
    current: current,
    baseline: baseline
  };
}

function getCurrentMetrics() {
  // This would be implemented to fetch current test metrics
  // For now, return placeholder values
  return {
    avg_response_time: 600,
    p95_response_time: 1200,
    error_rate: 0.03,
    throughput: 55
  };
}
