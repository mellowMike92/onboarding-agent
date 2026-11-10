import type { Milestone, MilestoneStatus, TimelineBucket } from '../types';
import MilestoneCard from './MilestoneCard';

const BUCKETS: { key: TimelineBucket; label: string }[] = [
  { key: '30_day', label: '30 Days' },
  { key: '60_day', label: '60 Days' },
  { key: '90_day', label: '90 Days' },
];

interface Props {
  milestones: Milestone[];
  onAdvance: (id: number, status: MilestoneStatus) => void;
}

export default function RoadmapBoard({ milestones, onAdvance }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {BUCKETS.map(({ key, label }) => {
        const items = milestones.filter((m) => m.timeline_bucket === key);
        const done = items.filter((m) => m.status === 'completed').length;
        return (
          <div
            key={key}
            className="rounded-xl border border-slate-800 bg-slate-900/40 p-4"
          >
            <div className="mb-3 flex items-baseline justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-cyan-400">
                {label}
              </h3>
              <span className="text-xs text-slate-500">
                {done}/{items.length} done
              </span>
            </div>
            <div className="space-y-3">
              {items.map((m) => (
                <MilestoneCard key={m.id} milestone={m} onAdvance={onAdvance} />
              ))}
              {items.length === 0 && (
                <p className="rounded-lg border border-dashed border-slate-800 p-4 text-center text-xs text-slate-600">
                  No milestones yet — run the agent.
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
