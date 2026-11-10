import type { Milestone, MilestoneStatus, Workflow } from './types';

const BASE = '/api';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`${init?.method ?? 'GET'} ${path} -> ${resp.status}`);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  listWorkflows: () => req<Workflow[]>('/workflows'),
  getWorkflow: (id: number) => req<Workflow>(`/workflows/${id}`),
  createWorkflow: (body: {
    user_name: string;
    role: string;
    tech_stack: string;
  }) => req<Workflow>('/workflows', { method: 'POST', body: JSON.stringify(body) }),
  runAgent: (id: number, instruction: string) =>
    req(`/workflows/${id}/run`, {
      method: 'POST',
      body: JSON.stringify({ instruction }),
    }),
  updateMilestone: (id: number, body: { status?: MilestoneStatus }) =>
    req<Milestone>(`/milestones/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  sendEvent: (body: {
    workflow_id: number;
    source: string;
    event_type: string;
    payload: Record<string, unknown>;
  }) => req('/webhooks/events', { method: 'POST', body: JSON.stringify(body) }),
};

export function openStream(
  workflowId: number,
  onEvent: (event: string, data: unknown) => void,
): () => void {
  const es = new EventSource(`${BASE}/workflows/${workflowId}/stream`);
  const events = [
    'ready',
    'tool_call',
    'tool_result',
    'agent_message',
    'agent_status',
    'milestone_updated',
    'done',
  ];
  for (const name of events) {
    es.addEventListener(name, (e) =>
      onEvent(name, JSON.parse((e as MessageEvent).data)),
    );
  }
  return () => es.close();
}
