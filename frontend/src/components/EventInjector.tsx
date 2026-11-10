import { GitPullRequest, Laptop, ShieldAlert, UserX, Zap } from 'lucide-react';

interface Props {
  disabled: boolean;
  onEvent: (source: string, eventType: string) => void;
}

const EVENTS = [
  {
    eventType: 'laptop_delayed',
    source: 'itsm',
    label: 'Laptop delayed',
    icon: Laptop,
    hint: 'Hardware ETA slips — front-load non-laptop work',
  },
  {
    eventType: 'first_pr_merged',
    source: 'github',
    label: 'First PR merged',
    icon: GitPullRequest,
    hint: 'Ahead of plan — accelerate technical milestones',
  },
  {
    eventType: 'mentor_out',
    source: 'hris',
    label: 'Mentor unavailable',
    icon: UserX,
    hint: 'Reassign pairing sessions to a backup mentor',
  },
  {
    eventType: 'security_blocker',
    source: 'itsm',
    label: 'Access blocked',
    icon: ShieldAlert,
    hint: 'Escalate and re-sequence blocked tasks',
  },
];

export default function EventInjector({ disabled, onEvent }: Props) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-1 flex items-center gap-2">
        <Zap className="h-5 w-5 text-cyan-400" />
        <h2 className="text-lg font-semibold text-slate-100">Simulate Events</h2>
      </div>
      <p className="mb-4 text-xs text-slate-500">
        Fire a webhook into the agent — watch it adapt the roadmap live.
      </p>
      <div className="grid gap-2">
        {EVENTS.map(({ eventType, source, label, icon: Icon, hint }) => (
          <button
            key={eventType}
            disabled={disabled}
            title={hint}
            onClick={() => onEvent(source, eventType)}
            className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-left text-sm text-slate-300 transition hover:border-cyan-500/50 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Icon className="h-4 w-4 shrink-0 text-cyan-400" />
            <span>
              <span className="block font-medium">{label}</span>
              <span className="block text-xs text-slate-500">
                {source}.{eventType}
              </span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
