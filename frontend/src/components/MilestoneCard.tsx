import { ArrowRight, CheckCircle2, Circle, Link2, Loader } from 'lucide-react';
import type { Milestone, MilestoneStatus } from '../types';

const STATUS_STYLE: Record<MilestoneStatus, { chip: string; icon: typeof Circle }> = {
  pending: { chip: 'border-slate-600 text-slate-400', icon: Circle },
  in_progress: { chip: 'border-amber-500/50 text-amber-300', icon: Loader },
  completed: { chip: 'border-emerald-500/50 text-emerald-300', icon: CheckCircle2 },
  adapted: { chip: 'border-cyan-500/50 text-cyan-300', icon: ArrowRight },
};

const NEXT: Partial<Record<MilestoneStatus, MilestoneStatus>> = {
  pending: 'in_progress',
  in_progress: 'completed',
  adapted: 'in_progress',
};

interface Props {
  milestone: Milestone;
  onAdvance: (id: number, status: MilestoneStatus) => void;
}

export default function MilestoneCard({ milestone, onAdvance }: Props) {
  const { chip, icon: Icon } = STATUS_STYLE[milestone.status];
  const next = NEXT[milestone.status];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-medium leading-snug text-slate-200">
          {milestone.title}
        </h4>
        <span
          className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${chip}`}
        >
          <Icon className="h-3 w-3" />
          {milestone.status.replace('_', ' ')}
        </span>
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
        {milestone.description}
      </p>
      {milestone.dependencies.length > 0 && (
        <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-600">
          <Link2 className="h-3 w-3" />
          depends on: {milestone.dependencies.join(', ')}
        </p>
      )}
      {next && (
        <button
          onClick={() => onAdvance(milestone.id, next)}
          className="mt-2.5 inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-[11px] font-medium text-slate-400 transition hover:border-cyan-500/50 hover:text-cyan-300"
        >
          mark {next.replace('_', ' ')}
          <ArrowRight className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}
