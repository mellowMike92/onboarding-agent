export type TimelineBucket = '30_day' | '60_day' | '90_day';
export type MilestoneStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'adapted';

export interface Milestone {
  id: number;
  workflow_id: number;
  title: string;
  timeline_bucket: TimelineBucket;
  status: MilestoneStatus;
  description: string;
  dependencies: string[];
}

export interface Workflow {
  id: number;
  user_name: string;
  role: string;
  tech_stack: string;
  status: MilestoneStatus;
  created_at: string;
  updated_at: string;
  milestones: Milestone[];
}

export interface FeedItem {
  id: number;
  kind:
    | 'tool_call'
    | 'tool_result'
    | 'agent_message'
    | 'agent_status'
    | 'milestone_updated'
    | 'system';
  text: string;
  detail?: string;
  at: Date;
}
