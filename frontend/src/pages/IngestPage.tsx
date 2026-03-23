import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/api';
import { EpisodeIngestStatus, IngestEpisodeState, IngestJobRead, ManifestSummary } from '../types/api';

const JOB_STORAGE_KEY = 'demo.jobId';
const MANIFEST_STORAGE_KEY = 'ingest.manifestPath';

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '任务操作失败，请稍后再试。';
}

function getEpisodeStateLabel(state: IngestEpisodeState): string {
  switch (state) {
    case 'queued':
      return '排队中';
    case 'running':
      return '入库中';
    case 'failed':
      return '失败';
    case 'ingested':
      return '已入库';
    default:
      return '未入库';
  }
}

function getEpisodeStateClassName(state: IngestEpisodeState): string {
  if (state === 'ingested') {
    return 'bg-[#edf8f1] text-success border-[rgba(47,125,87,0.16)]';
  }
  if (state === 'failed') {
    return 'bg-[#fff0ec] text-danger border-[rgba(176,73,58,0.16)]';
  }
  if (state === 'queued' || state === 'running') {
    return 'bg-[#fff7ea] text-accent border-[rgba(158,79,43,0.16)]';
  }
  return 'bg-white/90 text-muted border-line';
}

export const IngestPage: React.FC = () => {
  const [manifests, setManifests] = useState<ManifestSummary[]>([]);
  const [selectedManifestPath, setSelectedManifestPath] = useState('');
  const [episodes, setEpisodes] = useState<EpisodeIngestStatus[]>([]);
  const [job, setJob] = useState<IngestJobRead | null>(null);
  const [loadingManifests, setLoadingManifests] = useState(false);
  const [loadingEpisodes, setLoadingEpisodes] = useState(false);
  const [loadingJob, setLoadingJob] = useState(false);
  const [submittingEpisodeId, setSubmittingEpisodeId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const episodeRequestIdRef = useRef(0);

  const selectedManifest = useMemo(
    () => manifests.find((item) => item.manifest_path === selectedManifestPath) ?? null,
    [manifests, selectedManifestPath],
  );

  const episodeStats = useMemo(() => {
    const total = episodes.length;
    const ingested = episodes.filter((episode) => episode.is_ingested).length;
    const running = episodes.filter((episode) => episode.ingest_state === 'running').length;
    const queued = episodes.filter((episode) => episode.ingest_state === 'queued').length;
    const failed = episodes.filter((episode) => episode.ingest_state === 'failed').length;
    return { total, ingested, running, queued, failed };
  }, [episodes]);

  const loadManifests = useCallback(async (preferredManifestPath?: string) => {
    setLoadingManifests(true);
    try {
      const data = await api.getIngestManifests();
      setManifests(data);

      const savedManifestPath = localStorage.getItem(MANIFEST_STORAGE_KEY);
      setSelectedManifestPath((currentManifestPath) => [preferredManifestPath, savedManifestPath, currentManifestPath]
        .filter((value): value is string => Boolean(value))
        .find((value) => data.some((item) => item.manifest_path === value))
        ?? data[0]?.manifest_path
        ?? '');
    } catch (loadError: unknown) {
      setError(getErrorMessage(loadError));
      setManifests([]);
      setSelectedManifestPath('');
    } finally {
      setLoadingManifests(false);
    }
  }, []);

  const loadEpisodes = useCallback(async (manifestPath: string) => {
    if (!manifestPath) {
      episodeRequestIdRef.current += 1;
      setLoadingEpisodes(false);
      setEpisodes([]);
      return;
    }

    const requestId = episodeRequestIdRef.current + 1;
    episodeRequestIdRef.current = requestId;
    setLoadingEpisodes(true);
    try {
      const data = await api.getManifestEpisodes(manifestPath);
      if (episodeRequestIdRef.current !== requestId) {
        return;
      }
      setEpisodes(data);
      localStorage.setItem(MANIFEST_STORAGE_KEY, manifestPath);
    } catch (loadError: unknown) {
      if (episodeRequestIdRef.current !== requestId) {
        return;
      }
      setError(getErrorMessage(loadError));
    } finally {
      if (episodeRequestIdRef.current === requestId) {
        setLoadingEpisodes(false);
      }
    }
  }, []);

  const pollJob = async (jobId?: string) => {
    const id = jobId || job?.id;
    if (!id) {
      setError('请先提交一个任务。');
      return;
    }

    setLoadingJob(true);
    setError(null);
    try {
      const data = await api.getIngestJob(id);
      setJob(data);
      localStorage.setItem(JOB_STORAGE_KEY, data.id);
      if (selectedManifestPath) {
        await loadEpisodes(selectedManifestPath);
      }
    } catch (pollError: unknown) {
      setError(getErrorMessage(pollError));
    } finally {
      setLoadingJob(false);
    }
  };

  const handleSubmitEpisode = async (episode: EpisodeIngestStatus) => {
    if (!selectedManifest) {
      setError('请先选择一个 manifest。');
      return;
    }

    setSubmittingEpisodeId(episode.episode_id);
    setError(null);
    try {
      const data = await api.submitIngest({
        manifest_path: selectedManifest.manifest_path,
        series_id: selectedManifest.series_id,
        episode_id: episode.episode_id,
      });
      setJob(data);
      localStorage.setItem(JOB_STORAGE_KEY, data.id);
      await loadEpisodes(selectedManifest.manifest_path);
    } catch (submitError: unknown) {
      setError(getErrorMessage(submitError));
    } finally {
      setSubmittingEpisodeId(null);
    }
  };

  useEffect(() => {
    loadManifests();

    const savedJobId = localStorage.getItem(JOB_STORAGE_KEY);
    if (savedJobId) {
      setLoadingJob(true);
      api.getIngestJob(savedJobId)
        .then((data) => setJob(data))
        .catch((loadError: unknown) => setError(getErrorMessage(loadError)))
        .finally(() => setLoadingJob(false));
    }
  }, [loadManifests]);

  useEffect(() => {
    if (!selectedManifestPath) {
      setEpisodes([]);
      return;
    }
    loadEpisodes(selectedManifestPath);
  }, [loadEpisodes, selectedManifestPath]);



  return (
    <section className="ingest-grid grid grid-cols-1 lg:grid-cols-[1.12fr_0.88fr] gap-[18px]">
        <div className="stack grid gap-[18px]">
          <section className="panel grid gap-4">


            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
              <div>
                <label htmlFor="manifestSelect" className="block mb-1.5 text-muted text-xs font-sans">Manifest</label>
                <select
                  id="manifestSelect"
                  className="w-full"
                  value={selectedManifestPath}
                  onChange={(event) => {
                    setError(null);
                    setSelectedManifestPath(event.target.value);
                  }}
                  disabled={loadingManifests || manifests.length === 0}
                >
                  {manifests.length === 0 ? (
                    <option value="">当前未发现可用 manifest</option>
                  ) : (
                    manifests.map((manifest) => (
                      <option key={manifest.manifest_path} value={manifest.manifest_path}>
                        {manifest.series_title} · {manifest.series_id}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <button
                type="button"
                className="secondary"
                onClick={() => loadManifests(selectedManifestPath)}
                disabled={loadingManifests || loadingEpisodes}
              >
                {loadingManifests ? '刷新中...' : '刷新 manifest'}
              </button>
            </div>

            {selectedManifest ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <div className="rounded-[18px] border border-line bg-white/72 px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.12em] text-muted font-sans">剧集</div>
                  <div className="mt-1 text-lg font-bold">{selectedManifest.series_title}</div>
                  <div className="mt-1 text-xs text-muted font-sans">{selectedManifest.series_id}</div>
                </div>
                <div className="rounded-[18px] border border-line bg-white/72 px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.12em] text-muted font-sans">Season</div>
                  <div className="mt-1 text-lg font-bold">{selectedManifest.season_label || '未填写'}</div>
                  <div className="mt-1 text-xs text-muted font-sans">路径已锁定到所选 manifest</div>
                </div>
                <div className="rounded-[18px] border border-line bg-white/72 px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.12em] text-muted font-sans">已入库</div>
                  <div className="mt-1 text-lg font-bold">{episodeStats.ingested} / {episodeStats.total}</div>
                  <div className="mt-1 text-xs text-muted font-sans">进行中 {episodeStats.running + episodeStats.queued} · 失败 {episodeStats.failed}</div>
                </div>
              </div>
            ) : null}

            {loadingEpisodes ? (
              <div className="rounded-[20px] border border-line bg-white/70 px-5 py-8 text-center text-muted font-sans text-sm">
                正在同步 manifest 并加载 episode 状态...
              </div>
            ) : episodes.length > 0 ? (
              <div className="grid gap-3">
                {episodes.map((episode) => {
                  const isSubmitting = submittingEpisodeId === episode.episode_id;
                  return (
                    <article
                      key={episode.episode_id}
                      className="rounded-[22px] border border-line bg-panel-strong p-5 grid gap-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="text-sm uppercase tracking-[0.14em] text-muted font-sans">
                            <div>{episode.title} · {episode.episode_id}</div>
                          </div>
                        </div>
                        <div className={`rounded-full border px-3 py-2 text-xs font-sans ${getEpisodeStateClassName(episode.ingest_state)}`}>
                          {getEpisodeStateLabel(episode.ingest_state)}
                        </div>
                      </div>

                      <div className="grid gap-2 md:grid-cols-3 text-sm font-sans text-muted">
                        <div className="rounded-2xl border border-line bg-white/70 px-3 py-2">
                          frame 数：<span className="text-text font-semibold">{episode.frame_count}</span>
                        </div>
                        <div className="rounded-2xl border border-line bg-white/70 px-3 py-2">
                          最近任务：<span className="text-text font-semibold">{episode.latest_job_status || '无'}</span>
                        </div>
                        <div className="rounded-2xl border border-line bg-white/70 px-3 py-2">
                          阶段：<span className="text-text font-semibold">{episode.latest_job_stage || '-'}</span>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="text-xs text-muted font-sans leading-relaxed">
                          {episode.latest_error_message
                            ? `最近错误：${episode.latest_error_message}`
                            : episode.latest_finished_at
                              ? `最近完成时间：${new Date(episode.latest_finished_at).toLocaleString('zh-CN')}`
                              : '尚未发现完成记录，可以直接发起入库。'}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {episode.latest_job_id ? (
                            <button
                              type="button"
                              className="secondary"
                              onClick={() => pollJob(episode.latest_job_id || undefined)}
                              disabled={loadingJob}
                            >
                              查看最近任务
                            </button>
                          ) : null}
                          <button
                            type="button"
                            className="primary"
                            onClick={() => handleSubmitEpisode(episode)}
                            disabled={Boolean(submittingEpisodeId) || loadingEpisodes || loadingManifests}
                          >
                            {isSubmitting ? '提交中...' : episode.is_ingested ? '重新入库' : '提交入库'}
                          </button>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="rounded-[20px] border border-dashed border-line bg-white/65 px-5 py-8 text-center text-muted font-sans text-sm leading-relaxed">
                {selectedManifestPath
                  ? '当前 manifest 下没有可展示的 episode。若刚刚请求失败，请先看右侧错误提示后重试。'
                  : '请先选择一个 manifest。'}
              </div>
            )}
          </section>
        </div>

        <div className="stack grid gap-[18px] lg:sticky lg:top-[90px] self-start">
          <section className="panel status-card grid gap-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-baseline gap-2">
                <h2 className="m-0 text-xl font-bold">任务状态</h2>
                {job?.id && (
                  <span className="text-muted text-[11px] font-mono opacity-50 truncate max-w-[140px]" title={job.id || undefined}>
                    {job.id}
                  </span>
                )}
              </div>
              <button
                type="button"
                className="secondary w-9 h-9 p-0 flex items-center justify-center rounded-xl"
                onClick={() => pollJob()}
                disabled={loadingJob || !job?.id}
                title="刷新状态"
              >
                <svg className={`w-4 h-4 ${loadingJob ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true" role="img">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>

            <div className="status-strip flex flex-wrap gap-2.5">

              <div className="pill px-3 py-2 rounded-full bg-white/90 border border-line text-xs font-sans">
                状态：<span className="text-muted">{job?.status || '-'}</span>
              </div>
              <div className="pill px-3 py-2 rounded-full bg-white/90 border border-line text-xs font-sans">
                阶段：<span className="text-muted">{job?.current_stage || '-'}</span>
              </div>
              <div className="pill px-3 py-2 rounded-full bg-white/90 border border-line text-xs font-sans">
                进度：<span className="text-muted">{job?.progress_current ?? 0} / {job?.progress_total ?? 0}</span>
              </div>
              <div className="pill px-3 py-2 rounded-full bg-white/90 border border-line text-xs font-sans">
                图片向量：<span className="text-muted">{job?.artifacts?.embedding_status || '-'}</span>
              </div>
            </div>



            <div className="muted text-muted font-sans text-sm leading-relaxed">
              {error ? (
                <span className="text-danger">{error}</span>
              ) : job ? (
                <span className={job.status === 'completed' ? 'text-success' : job.status === 'failed' ? 'text-danger' : ''}>
                  {job.error_message ? `错误：${job.error_message}` : '任务记录已更新。'}
                  {job.artifacts?.embedding_status && ` 图片向量状态：${job.artifacts.embedding_status}。`}
                </span>
              ) : (
                '从左侧列表点击“提交入库”后，这里会显示最近一次任务状态。'
              )}
            </div>

            <div className="json-box mt-2">
              {JSON.stringify(job || {}, null, 2)}
            </div>
          </section>
        </div>
      </section>
  );
};
