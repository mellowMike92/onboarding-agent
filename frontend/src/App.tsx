import { Bot, RefreshCcw } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api, openStream } from './api';
import AgentStream from './components/AgentStream';
import EventInjector from './components/EventInjector';
import RoadmapBoard from './components/RoadmapBoard';
import WorkflowCreator from './components/WorkflowCreator';
import type { FeedItem, MilestoneStatus, Workflow } from './types';

export default function App() {
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [agentRunning, setAgentRunning] = useState(false);
  const feedId = useRef(0);

  const pushFeed = useCallback((kind: FeedItem['kind'], text: string, detail?: string) => {
    setFeed((f) => [...f.slice(-199), { id: ++feedId.current, kind, text, detail, at: new Date() }]);
  }, []);

  const refresh = useCallback(async (id: number) => {
    setWorkflow(await api.getWorkflow(id));
  }, []);

  useEffect(() => {
    api.listWorkflows().then((wfs) => {
      if (wfs.length > 0) setWorkflow(wfs[0]);
    });
  }, []);

  useEffect(() => {
    if (!workflow) return;
    const id = workflow.id;
    const close = openStream(id, (event, raw) => {
      const data = raw as Record<string, unknown>;
      if (event === 'tool_call') {
        pushFeed('tool_call', `tool_call ${data.name}`, JSON.stringify(data.input));
      } else if (event === 'tool_result') {
        pushFeed('tool_result', `tool_result ${data.name}`, JSON.stringify(data.result));
        void refresh(id);
      } else if (event === 'agent_message') {
        pushFeed('agent_message', String(data.text));
      } else if (event === 'agent_status') {
        const status = String(data.status);
        setAgentRunning(status === 'running');
        if (status === 'error') pushFeed('system', `agent error: ${data.detail}`);
        void refresh(id);
      } else if (event === 'milestone_updated') {
        pushFeed('milestone_updated', `milestone #${data.id} → ${data.status}`);
        void refresh(id);
      }
    });
    return close;
  }, [workflow?.id, pushFeed, refresh]);

  const createAndRun = async (input: {
    user_name: string;
    role: string;
    tech_stack: string;
  }) => {
    setBusy(true);
    try {
      const wf = await api.createWorkflow(input);
      setWorkflow(wf);
      pushFeed('system', `workflow #${wf.id} created for ${wf.user_name}`);
      setAgentRunning(true);
      await api.runAgent(wf.id, 'Generate the 30/60/90-day onboarding roadmap.');
    } catch (e) {
      pushFeed('system', `error: ${e instanceof Error ? e.message : String(e)}`);
      setAgentRunning(false);
    } finally {
      setBusy(false);
    }
  };

  const fireEvent = async (source: string, eventType: string) => {
    if (!workflow) return;
    pushFeed('system', `webhook → ${source}.${eventType}`);
    setAgentRunning(true);
    await api.sendEvent({
      workflow_id: workflow.id,
      source,
      event_type: eventType,
      payload: { fired_from: 'demo-ui', at: new Date().toISOString() },
    });
  };

  const advanceMilestone = async (id: number, status: MilestoneStatus) => {
    await api.updateMilestone(id, { status });
    if (workflow) await refresh(workflow.id);
  };

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-8">
      <header className="mb-8 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-2">
            <Bot className="h-6 w-6 text-cyan-400" />
          </span>
          <div>
            <h1 className="text-2xl font-bold text-slate-50">onboarding-agent</h1>
            <p className="text-sm text-slate-400">
              Dynamic 30/60/90-day onboarding workflows, adapted live by a tool-calling agent
            </p>
          </div>
        </div>
        {workflow && (
          <div className="ml-auto flex items-center gap-3">
            {agentRunning && (
              <RefreshCcw className="h-4 w-4 animate-spin text-cyan-400" />
            )}
            <span
              className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                workflow.status === 'adapted'
                  ? 'border-cyan-500/40 text-cyan-300'
                  : workflow.status === 'in_progress'
                    ? 'border-amber-500/40 text-amber-300'
                    : 'border-slate-600 text-slate-400'
              }`}
            >
              #{workflow.id} · {workflow.status.replace('_', ' ')}
            </span>
          </div>
        )}
      </header>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr_360px]">
        <div className="space-y-6">
          <WorkflowCreator busy={busy} onCreate={createAndRun} />
          <EventInjector disabled={!workflow || agentRunning} onEvent={fireEvent} />
        </div>

        <section>
          {workflow ? (
            <>
              <div className="mb-4 rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-100">
                  {workflow.user_name}
                  <span className="text-slate-500"> — {workflow.role}</span>
                </h2>
                <p className="text-sm text-slate-500">{workflow.tech_stack}</p>
              </div>
              <RoadmapBoard
                milestones={workflow.milestones}
                onAdvance={advanceMilestone}
              />
            </>
          ) : (
            <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-slate-800 text-sm text-slate-600">
              Create a workflow to generate a 30/60/90-day onboarding roadmap.
            </div>
          )}
        </section>

        <div className="min-h-[400px] lg:sticky lg:top-8 lg:h-[calc(100vh-8rem)]">
          <AgentStream feed={feed} />
        </div>
      </div>
    </main>
  );
}
