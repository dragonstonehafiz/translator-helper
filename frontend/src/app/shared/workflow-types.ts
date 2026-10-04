/** Backend workflow IDs, as returned in `data.workflow` by every start endpoint and polled at /task-results/{workflow}. */
export const WORKFLOW_TYPES = {
  translateLine: 'translate_line',
  translateFile: 'translate_file',
  reviewTranslatedFile: 'review_file',
  transcribeClip: 'transcribe_clip',
  transcribeFile: 'transcribe_file',
  updateLibrary: 'update_library',
} as const;

export type WorkflowId = typeof WORKFLOW_TYPES[keyof typeof WORKFLOW_TYPES];

export type WorkflowStatus = 'idle' | 'processing' | 'complete' | 'error';

export interface CharacterUpdateProposal {
  id: string;
  field: string;
  append: string;
  character?: string;
}

export interface GlossaryUpdateProposal {
  id: string;
  field: string;
  value: string;
}

export interface NewCharacterProposal {
  name: string;
  aliases: string[];
  personality: string[];
  relationships: { [character: string]: string[] };
  history: string[];
}

export interface NewGlossaryProposal {
  term: string;
  translation: string;
  notes: string;
}

export interface LibraryProposals {
  new_characters: NewCharacterProposal[];
  updated_characters: CharacterUpdateProposal[];
  new_glossary: NewGlossaryProposal[];
  updated_glossary: GlossaryUpdateProposal[];
}

/** Result of translate_line and transcribe_clip. */
export interface TextResult {
  text: string;
}

/** Result of translate_file and transcribe_file. */
export interface FileResult {
  output_filename: string;
  folder: string;
}

/** Result of review_file. */
export interface ReviewFileResult extends FileResult {
  corrected_count: number;
}

/** Result of update_library. */
export interface ProposalResult {
  proposals: LibraryProposals;
}

export type WorkflowResult = TextResult | FileResult | ReviewFileResult | ProposalResult;

export interface WorkflowStartData {
  workflow: WorkflowId;
}

/** `data` of a /task-results/{workflow} response; only `workflow` is present while idle. */
export interface WorkflowResultData {
  workflow: WorkflowId;
  active_task?: string | null;
  progress?: [number, number];
  message?: string;
  eta_seconds?: number;
  result?: WorkflowResult | null;
}

/** Frontend copy of one workflow's latest state. */
export interface WorkflowState {
  workflow: WorkflowId;
  status: WorkflowStatus;
  activeTask: string | null;
  current: number;
  total: number;
  message: string;
  etaSeconds: number;
  result: WorkflowResult | null;
  error: string | null;
  /** Series a library update was started for; set by the frontend, not the backend. */
  seriesId: string | null;
}

export function isTextResult(result: WorkflowResult | null): result is TextResult {
  return result !== null && 'text' in result;
}

export function isProposalResult(result: WorkflowResult | null): result is ProposalResult {
  return result !== null && 'proposals' in result;
}
