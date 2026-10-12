/**
 * Realistic initial enterprise datasets and state for DataReliant Dashboard.
 */

export const INITIAL_DATASETS = [
  {
    id: "ds_cust_001",
    name: "customers",
    format: "parquet",
    row_count: 50000,
    column_count: 6,
    size_mb: 4.2,
    null_rate: 0.002,
    status: "HEALTHY",
    last_profiled: "2026-10-10 14:20:00 UTC",
    columns: [
      { name: "customer_id", type: "Utf8", null_count: 0, distinct: 50000, is_key: true },
      { name: "country", type: "Utf8", null_count: 12, distinct: 8, is_key: false },
      { name: "segment", type: "Utf8", null_count: 0, distinct: 3, is_key: false },
      { name: "credit_score", type: "Int64", null_count: 50, distinct: 540, min: 310, max: 850, mean: 712.4 },
      { name: "account_balance", type: "Float64", null_count: 42, distinct: 48920, min: 12.5, max: 125000.0, mean: 4210.8 },
      { name: "created_at", type: "Datetime", null_count: 0, min: "2024-01-01", max: "2026-10-09" }
    ]
  },
  {
    id: "ds_prod_002",
    name: "products",
    format: "parquet",
    row_count: 1200,
    column_count: 5,
    size_mb: 0.3,
    null_rate: 0.0,
    status: "HEALTHY",
    last_profiled: "2026-10-10 14:20:00 UTC",
    columns: [
      { name: "product_id", type: "Utf8", null_count: 0, distinct: 1200, is_key: true },
      { name: "category", type: "Utf8", null_count: 0, distinct: 5 },
      { name: "cost", type: "Float64", null_count: 0, min: 5.0, max: 480.0, mean: 94.2 },
      { name: "price", type: "Float64", null_count: 0, min: 9.99, max: 999.0, mean: 172.5 },
      { name: "stock_level", type: "Int64", null_count: 0, min: 0, max: 4800, mean: 850 }
    ]
  },
  {
    id: "ds_tx_003",
    name: "transactions",
    format: "parquet",
    row_count: 245000,
    column_count: 7,
    size_mb: 18.6,
    null_rate: 0.048,
    status: "WARNING",
    last_profiled: "2026-10-10 15:10:00 UTC",
    columns: [
      { name: "transaction_id", type: "Utf8", null_count: 0, distinct: 245000, is_key: true },
      { name: "customer_id", type: "Utf8", null_count: 0, distinct: 49800 },
      { name: "product_id", type: "Utf8", null_count: 0, distinct: 1200 },
      { name: "quantity", type: "Int64", null_count: 0, min: 1, max: 12, mean: 2.4 },
      { name: "amount", type: "Float64", null_count: 1120, min: 9.99, max: 14200.0, mean: 342.1 },
      { name: "channel", type: "Utf8", null_count: 0, distinct: 4 },
      { name: "timestamp", type: "Datetime", null_count: 0, min: "2025-01-01", max: "2026-10-10" }
    ]
  },
  {
    id: "ds_pay_004",
    name: "payments",
    format: "parquet",
    row_count: 242000,
    column_count: 7,
    size_mb: 16.1,
    null_rate: 0.001,
    status: "HEALTHY",
    last_profiled: "2026-10-10 15:12:00 UTC",
    columns: [
      { name: "payment_id", type: "Utf8", null_count: 0, distinct: 242000, is_key: true },
      { name: "transaction_id", type: "Utf8", null_count: 0, distinct: 242000 },
      { name: "method", type: "Utf8", null_count: 0, distinct: 4 },
      { name: "amount", type: "Float64", null_count: 0, min: 9.99, max: 14200.0, mean: 342.1 },
      { name: "fee", type: "Float64", null_count: 0, min: 0.5, max: 355.0, mean: 8.8 },
      { name: "status", type: "Utf8", null_count: 0, distinct: 3 },
      { name: "processed_at", type: "Datetime", null_count: 0 }
    ]
  }
];

export const INITIAL_QUALITY_RULES = [
  { id: "R01", type: "not_null", column: "customer_id", dataset: "customers", severity: "CRITICAL", status: "PASSED" },
  { id: "R02", type: "uniqueness", column: "customer_id", dataset: "customers", severity: "CRITICAL", status: "PASSED" },
  { id: "R03", type: "range", column: "amount", dataset: "transactions", params: { min: 0.01, max: 25000.0 }, severity: "HIGH", status: "PASSED" },
  { id: "R04", type: "categorical_values", column: "channel", dataset: "transactions", params: { allowed: ["WEB", "MOBILE_APP", "PARTNER_API", "IN_STORE"] }, severity: "HIGH", status: "PASSED" },
  { id: "R05", type: "referential_integrity", column: "customer_id", dataset: "transactions", params: { parent_dataset: "customers", parent_column: "customer_id" }, severity: "CRITICAL", status: "PASSED" },
  { id: "R06", type: "freshness", column: "timestamp", dataset: "transactions", params: { max_age_hours: 24 }, severity: "MEDIUM", status: "PASSED" },
  { id: "R07", type: "row_count", dataset: "transactions", params: { min_rows: 1000 }, severity: "HIGH", status: "PASSED" },
  { id: "R08", type: "schema", dataset: "transactions", severity: "CRITICAL", status: "PASSED" },
  { id: "R09", type: "duplicate_rows", dataset: "transactions", severity: "HIGH", status: "PASSED" },
  { id: "R10", type: "custom_expression", dataset: "transactions", params: { expr: "amount > 0" }, severity: "MEDIUM", status: "PASSED" }
];

export const INITIAL_ANOMALIES = [
  {
    id: "ANOM-901",
    detector: "zscore",
    dataset: "transactions",
    metric: "null_rate_amount",
    observed: 0.048,
    expected: 0.001,
    anomaly_score: 4.8,
    severity: "HIGH",
    detected_at: "2026-10-10 15:10:22 UTC"
  },
  {
    id: "ANOM-902",
    detector: "robust_zscore",
    dataset: "transactions",
    metric: "row_count",
    observed: 18200,
    expected: 25000,
    anomaly_score: 3.9,
    severity: "HIGH",
    detected_at: "2026-10-10 15:11:05 UTC"
  },
  {
    id: "ANOM-903",
    detector: "ks_test",
    dataset: "transactions",
    metric: "amount_distribution",
    observed: 0.0002,
    expected: 0.05,
    anomaly_score: 5.2,
    severity: "MEDIUM",
    detected_at: "2026-10-10 15:12:40 UTC"
  },
  {
    id: "ANOM-904",
    detector: "schema_drift",
    dataset: "transactions",
    metric: "unannounced_column",
    observed: 1.0,
    expected: 0.0,
    anomaly_score: 3.1,
    severity: "MEDIUM",
    detected_at: "2026-10-10 14:05:00 UTC"
  }
];

export const INITIAL_INCIDENTS = [
  {
    id: "INC-2026-081",
    title: "Transactions Ingestion Spike & Null Corruption",
    severity: "CRITICAL",
    status: "INVESTIGATING",
    start_time: "2026-10-10 15:08:00 UTC",
    affected_nodes: ["transactions", "payments", "analytics_mart"],
    anomaly_count: 3,
    compression_ratio: "3.0x",
    top_root_cause: {
      type: "NULL_SPIKE",
      confidence: 0.88,
      evidence_breakdown: {
        statistical: 0.95,
        graph: 0.70,
        temporal: 0.85,
        propagation: 0.60
      },
      evidence_items: [
        "Statistical null rate z-score 5.5x beyond normal baseline on 'amount'",
        "Earliest anomaly detected at 15:08:00 UTC during micro-batch ingestion",
        "Failure cascades downstream to 2 dependent operational tables"
      ]
    }
  },
  {
    id: "INC-2026-079",
    title: "Upstream Customer Source Cut-Off with Referential Breakage",
    severity: "HIGH",
    status: "RESOLVED",
    start_time: "2026-10-09 21:15:00 UTC",
    affected_nodes: ["customers", "transactions"],
    anomaly_count: 2,
    compression_ratio: "2.0x",
    top_root_cause: {
      type: "UPSTREAM_FAILURE",
      confidence: 0.92,
      evidence_breakdown: {
        graph: 1.0,
        statistical: 0.90,
        temporal: 0.80,
        propagation: 0.40
      },
      evidence_items: [
        "Upstream node 'customers' dropped 80% expected volume prior to downstream run",
        "Downstream orphan foreign key rate reached 150 missing parent keys"
      ]
    }
  }
];

export const LINEAGE_GRAPH_DATA = {
  nodes: [
    { id: "customers", name: "Customers (Postgres)", type: "source", x: 100, y: 150, rows: "50,000", status: "HEALTHY" },
    { id: "products", name: "Products (Catalog)", type: "source", x: 100, y: 350, rows: "1,200", status: "HEALTHY" },
    { id: "transactions", name: "Transactions Engine", type: "table", x: 400, y: 250, rows: "245,000", status: "CRITICAL" },
    { id: "payments", name: "Payments Processing", type: "table", x: 700, y: 250, rows: "242,000", status: "WARNING" },
    { id: "analytics_mart", name: "Executive KPI Dashboard", type: "dashboard", x: 980, y: 250, rows: "Aggregated", status: "WARNING" }
  ],
  edges: [
    { source: "customers", target: "transactions" },
    { source: "products", target: "transactions" },
    { source: "transactions", target: "payments" },
    { source: "payments", target: "analytics_mart" }
  ]
};

export const BENCHMARK_SCENARIOS = [
  { id: "missing_rows", name: "Missing Rows", true_cause: "MISSING_DATA", category: "Volume Anomaly", desc: "Upstream cut-off drops 35% of rows" },
  { id: "duplicate_rows", name: "Duplicate Rows", true_cause: "DUPLICATE_INGESTION", category: "Idempotency", desc: "Ingestion retry reproduces duplicate batch" },
  { id: "null_spike", name: "Null Spike", true_cause: "NULL_SPIKE", category: "Integrity", desc: "45% null injection into key numeric feature" },
  { id: "schema_addition", name: "Schema Addition", true_cause: "SCHEMA_DRIFT", category: "Schema", desc: "Unannounced metadata field added upstream" },
  { id: "schema_removal", name: "Schema Removal", true_cause: "SCHEMA_DRIFT", category: "Schema", desc: "Breaking deletion of required column" },
  { id: "datatype_change", name: "Datatype Change", true_cause: "TYPE_CHANGE", category: "Schema", desc: "Numeric column corrupted into String" },
  { id: "range_violation", name: "Range Violation", true_cause: "TRANSFORMATION_ERROR", category: "Values", desc: "Extreme 20x outlier multiplier injected" },
  { id: "categorical_corruption", name: "Categorical Corruption", true_cause: "SOURCE_DATA_CHANGE", category: "Domain", desc: "Illegal enum status values injected" },
  { id: "distribution_shift", name: "Distribution Shift", true_cause: "DISTRIBUTION_SHIFT", category: "Statistics", desc: "Mean + variance drift shifted by +40" },
  { id: "timezone_shift", name: "Timezone Shift", true_cause: "TIMEZONE_MISMATCH", category: "Temporal", desc: "-5 hour offset unhandled timezone shift" },
  { id: "late_arrival", name: "Late Arrival", true_cause: "LATE_ARRIVAL", category: "Temporal", desc: "14-day delayed backdated records arrived" },
  { id: "upstream_failure", name: "Upstream Failure", true_cause: "UPSTREAM_FAILURE", category: "Graph", desc: "80% truncation of upstream dependency table" },
  { id: "mixed_failure", name: "Mixed Compound Failure", true_cause: "TRANSFORMATION_ERROR", category: "Compound", desc: "Triple anomaly: nulls + categoricals + extra column" }
];
