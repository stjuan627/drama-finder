import {
  EpisodeIngestStatus,
  IngestEpisodeRequest,
  IngestJobRead,
  ManifestSummary,
  SearchResponse,
  SearchTextRequest,
} from '../types/api';

interface ErrorPayload {
  detail?: string;
}

function isErrorPayload(value: unknown): value is ErrorPayload {
  return typeof value === 'object' && value !== null && 'detail' in value;
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload: unknown = await response.json();
    if (isErrorPayload(payload) && typeof payload.detail === 'string') {
      return payload.detail;
    }
  } catch {
    return fallback;
  }
  return fallback;
}

export const api = {
  async searchText(payload: SearchTextRequest): Promise<SearchResponse> {
    const response = await fetch('/search/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, 'Search failed'));
    }
    return response.json();
  },

  async searchImage(file: File): Promise<SearchResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('/search/image', {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, 'Image search failed'));
    }
    return response.json();
  },

  async submitIngest(payload: IngestEpisodeRequest): Promise<IngestJobRead> {
    const response = await fetch('/ingest/episode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, 'Ingest submission failed'));
    }
    return response.json();
  },

  async getIngestManifests(): Promise<ManifestSummary[]> {
    const response = await fetch('/ingest/manifests');
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, 'Failed to fetch manifests'));
    }
    return response.json();
  },

  async getManifestEpisodes(manifestPath: string): Promise<EpisodeIngestStatus[]> {
    const params = new URLSearchParams({ manifest_path: manifestPath });
    const response = await fetch(`/ingest/manifest-episodes?${params.toString()}`);
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, 'Failed to fetch manifest episodes'));
    }
    return response.json();
  },

  async getIngestJob(jobId: string): Promise<IngestJobRead> {
    const response = await fetch(`/ingest/${jobId}`);
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, 'Failed to fetch job status'));
    }
    return response.json();
  },

  getEvidenceUrl(path: string): string {
    return `/demo/evidence?path=${encodeURIComponent(path)}`;
  },
};
