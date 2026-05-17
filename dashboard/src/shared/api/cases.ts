import { apiClient } from "./client";
import type { CaseDetail, CaseListResponse, Priority } from "./types";

export async function listCases(params: {
  status?: string;
  page?: number;
  pageSize?: number;
}): Promise<CaseListResponse> {
  const { data } = await apiClient.get<CaseListResponse>("/cases", {
    params: {
      status: params.status,
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
    },
  });
  return data;
}

export async function getCase(id: string): Promise<CaseDetail> {
  const { data } = await apiClient.get<CaseDetail>(`/cases/${id}`);
  return data;
}

export async function cancelCase(id: string, reason?: string): Promise<CaseDetail> {
  const { data } = await apiClient.post<CaseDetail>(`/cases/${id}/cancel`, { reason });
  return data;
}

export async function createCase(payload: {
  title: string;
  description?: string;
  priority: Priority;
  files: File[];
}): Promise<{ id: string }> {
  const form = new FormData();
  form.append("title", payload.title);
  if (payload.description) form.append("description", payload.description);
  form.append("priority", payload.priority);
  for (const f of payload.files) form.append("files", f);

  const { data } = await apiClient.post<{ id: string }>("/cases", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getReportPresignedUrl(id: string): Promise<string> {
  const { data } = await apiClient.get<{ url: string }>(`/reports/${id}/presigned`);
  return data.url;
}
