export type CaseStatus =
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "retrying"
  | "cancelled";

export type Priority = "low" | "medium" | "high" | "critical";

export interface DataSource {
  id: string;
  type: string;
  storage_key: string;
  original_filename: string | null;
  mime_type: string | null;
  size_bytes: number;
}

export interface Subtask {
  id: string;
  worker_type: string;
  status: string;
  attempts: number;
  priority: number;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export interface Finding {
  id: string;
  category: string;
  severity: number;
  confidence: number;
  evidence: Record<string, unknown>;
  created_at: string;
}

export interface CaseListItem {
  id: string;
  title: string;
  status: CaseStatus;
  priority: number;
  total_subtasks: number;
  completed_subtasks: number;
  failed_subtasks: number;
  created_at: string;
  finished_at: string | null;
}

export interface CaseListResponse {
  items: CaseListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface CaseDetail extends CaseListItem {
  description: string | null;
  report_storage_key: string | null;
  started_at: string | null;
  data_sources: DataSource[];
  subtasks: Subtask[];
  findings: Finding[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
}
