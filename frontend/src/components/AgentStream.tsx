import {
  Bot,
  CheckCheck,
  Hammer,
  MessageSquare,
  RefreshCcw,
  TerminalSquare,
} from 'lucide-react';
import { useEffect, useRef } from 'react';
import type { FeedItem } from '../types';

const KIND_STYLE: Record<FeedItem['kind'], { icon: typeof Bot; color: string }> = {
  tool_call: { icon: Hammer, color: 'text-amber-300' },
  tool_result: { icon: CheckCheck, color: 'text-emerald-300' },
  agent_message: { icon: MessageSquare, color: 'text-cyan-300' },
  agent_status: { icon: Bot, color: 'text-violet-300' },
  milestone_updated: { icon: RefreshCcw, color: 'text-sky-300' },
  system: { icon: TerminalSquare, color: 'text-slate-400' },
};

export default function AgentStream({ feed }: { feed: FeedItem[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [feed.length]);

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-800 bg-slate-950">
      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-3">
        <TerminalSquare className="h-4 w-4 text-cyan-400" />
        <h2 className="text-sm font-semibold text-slate-200">
          Agent Execution Stream
        </h2>
        <span className="ml-auto rounded-full border border-slate-700 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-500">
          SSE · live
        </span>
      </div>
      <div className="flex-1 space-y-1.5 overflow-y-auto p-4 font-mono text-xs">
        {feed.length === 0 && (
          <p className="text-slate-600">
            $ waiting for agent activity… create a workflow to begin.
          </p>
        )}
        {feed.map((item) => {
          const { icon: Icon, color } = KIND_STYLE[item.kind];
          return (
            <div key={item.id} className="flex items-start gap-2">
              <Icon className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${color}`} />
              <div className="min-w-0">
                <span className="text-slate-600">
                  {item.at.toLocaleTimeString()}{' '}
                </span>
                <span className="text-slate-300">{item.text}</span>
                {item.detail && (
                  <pre className="mt-0.5 max-h-24 overflow-y-auto whitespace-pre-wrap break-words text-[10px] text-slate-600">
                    {item.detail}
                  </pre>
                )}
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
}
