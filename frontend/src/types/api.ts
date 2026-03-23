export type JobStatus = 'queued' | 'running' | 'failed' | 'completed';

export type IngestEpisodeState = 'not_ingested' | 'ingested' | JobStatus;

export type JobStage =
  | 'manifest'
  | 'audio_extraction'
  | 'asr'
  | 'shot_detection'
  | 'frame_extraction'
  | 'representative_frames'
  | 'scene_merge'
  | 'embeddings'
  | 'persist';

export interface SearchHit {
  series_id: string;
  episode_id: string;
  series_label: string;
  episode_label: string;
  matched_start_ts: number;
  matched_end_ts: number;
  score: number;
  evidence_images: string[];
  evidence_text: string[];
}

export interface SearchResponse {
  hits: SearchHit[];
  low_confidence: boolean;
}

export interface SearchTextRequest {
  query: string;
  limit?: number;
}

export interface IngestEpisodeRequest {
  manifest_path: string;
  series_id: string;
  episode_id: string;
}

export interface ManifestSummary {
  manifest_path: string;
  series_id: string;
  series_title: string;
  season_label: string | null;
  language: string;
  episode_count: number;
}

export interface EpisodeIngestStatus {
  episode_id: string;
  episode_no: number;
  title: string;
  filename: string;
  ingest_state: IngestEpisodeState;
  is_ingested: boolean;
  frame_count: number;
  latest_job_id: string | null;
  latest_job_status: JobStatus | null;
  latest_job_stage: JobStage | null;
  latest_error_message: string | null;
  latest_finished_at: string | null;
}

export interface EmbeddingProgress {
  pending?: number;
  processed?: number;
  updated?: number;
  failed?: number;
  remaining?: number;
}

export interface IngestArtifacts extends Record<string, unknown> {
  embedding_status?: string;
  embedding_progress?: EmbeddingProgress;
  pending_frame_embeddings?: number;
}

export interface IngestJobRead {
  id: string;
  series_pk: string;
  episode_pk: string;
  status: JobStatus;
  current_stage: JobStage | null;
  progress_current: number;
  progress_total: number;
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  artifacts: IngestArtifacts;
}
