// Q-Sentinel Mesh — TypeScript interfaces matching all API response shapes

export interface HealthResponse {
  status: "ok";
  model_loaded: boolean;
  device: string;
}

// Hemorrhage subtypes
export type HemorrhageType =
  | "epidural"
  | "intraparenchymal"
  | "intraventricular"
  | "subarachnoid"
  | "subdural"
  | "any";

export type HemorrhageProbabilities = Record<HemorrhageType, number>;
export type HemorrhageThresholds = Record<HemorrhageType, number>;

// CT Upload & Window
export interface CTUploadResponse {
  s3_key: string;
  slice_count: number;
  shape: [number, number, number]; // [D, H, W]
  min_hu: number;
  max_hu: number;
  filename: string;
}

export type WindowPreset = "brain" | "blood" | "subdural" | "bone" | "wide";

export interface CTWindowRequest {
  s3_key: string;
  slice_idx: number;
  window: WindowPreset;
}

export interface CTWindowResponse {
  image_b64: string; // "data:image/png;base64,..."
  hu_stats: {
    mean: number;
    std: number;
    min: number;
    max: number;
  };
}

// Prediction
export type ModelType = "baseline" | "hybrid";

export interface PredictRequest {
  s3_key: string;
  slice_idx: number;
  model_type: ModelType;
  threshold?: number;
  auto_triage?: boolean;
}

export interface PredictResponse {
  probabilities: HemorrhageProbabilities;
  heatmap_b64: string; // base64 PNG
  top_class: HemorrhageType;
  confidence: number;
  slice_used: number;
  baseline_probs?: HemorrhageProbabilities; // for comparison card
  quantum_gain?: number; // hybrid vs baseline delta
}

// Benchmark metrics
export interface BenchmarkData {
  nodes: number[];
  baseline_auc: number[];
  qsentinel_auc: number[];
  labels: {
    baseline: string;
    qsentinel: string;
  };
  metadata: {
    baseline_best_auc: number;
    hybrid_best_auc: number;
    fed_final_auc: number;
    dataset: string;
  };
}

// Federated rounds
export interface HospitalRoundData {
  train_loss: number;
  num_examples: number;
  pqc_encrypted: boolean;
  quantum_layer: boolean;
  local_auc: number;
}

export interface FedRound {
  round: number;
  hospitals: Record<string, HospitalRoundData>;
  pqc_rounds: number;
  global_auc: number;
  global_loss: number;
}

// PQC demo
export interface PQCDemoResponse {
  public_key_bytes: number;
  secret_key_bytes: number;
  kem_ciphertext_bytes: number;
  aes_ciphertext_bytes: number;
  keygen_ms: number;
  encrypt_ms: number;
  decrypt_ms: number;
  success: boolean;
  backend: string;
  error?: string;
}
