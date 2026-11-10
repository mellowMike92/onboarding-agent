import { Loader2, Play, UserPlus } from 'lucide-react';
import { useState } from 'react';

interface Props {
  busy: boolean;
  onCreate: (input: {
    user_name: string;
    role: string;
    tech_stack: string;
  }) => void;
}

export default function WorkflowCreator({ busy, onCreate }: Props) {
  const [userName, setUserName] = useState('Grace Hopper');
  const [role, setRole] = useState('Backend Engineer');
  const [techStack, setTechStack] = useState('Python, FastAPI, Postgres');

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-4 flex items-center gap-2">
        <UserPlus className="h-5 w-5 text-cyan-400" />
        <h2 className="text-lg font-semibold text-slate-100">New Hire Workflow</h2>
      </div>
      <div className="space-y-3">
        <label className="block">
          <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
            Name
          </span>
          <input
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
            Role
          </span>
          <select
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            <option>Backend Engineer</option>
            <option>Frontend Engineer</option>
            <option>Data Scientist</option>
            <option>Engineering Manager</option>
            <option>Product Designer</option>
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
            Tech Stack
          </span>
          <input
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500"
            value={techStack}
            onChange={(e) => setTechStack(e.target.value)}
          />
        </label>
        <button
          disabled={busy || !userName.trim()}
          onClick={() =>
            onCreate({
              user_name: userName.trim(),
              role,
              tech_stack: techStack.trim(),
            })
          }
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          Create & Run Agent
        </button>
      </div>
    </div>
  );
}
