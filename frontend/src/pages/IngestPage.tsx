import React, { useState, useEffect } from 'react';
import { Hero } from '../components/Hero';
import { api } from '../api/api';
import { IngestJobRead } from '../types/api';

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '任务操作失败，请稍后再试。';
}

interface IngestPageProps {
  onNavigate: (page: 'search' | 'ingest') => void;
}

export const IngestPage: React.FC<IngestPageProps> = ({ onNavigate }) => {
  const [manifestPath, setManifestPath] = useState('/tmp/wufulinmen-test-manifest.yaml');
  const [seriesId, setSeriesId] = useState('wufulinmen');
  const [episodeId, setEpisodeId] = useState('ep02');
  const [job, setJob] = useState<IngestJobRead | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.submitIngest({
        manifest_path: manifestPath.trim(),
        series_id: seriesId.trim(),
        episode_id: episodeId.trim(),
      });
      setJob(data);
      localStorage.setItem('demo.jobId', data.id);
    } catch (error: unknown) {
      setError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  const pollJob = async (jobId?: string) => {
    const id = jobId || job?.id;
    if (!id) {
      setError('请先提交一个任务。');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getIngestJob(id);
      setJob(data);
    } catch (error: unknown) {
      setError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const savedJobId = localStorage.getItem('demo.jobId');
    if (savedJobId) {
      const id = savedJobId;
      setLoading(true);
      setError(null);
      api.getIngestJob(id)
        .then(data => setJob(data))
        .catch((error: unknown) => setError(getErrorMessage(error)))
        .finally(() => setLoading(false));
    }
  }, []);

  const embeddingProgress = job?.artifacts?.embedding_progress || {};
  const embeddingPending = embeddingProgress.pending ?? job?.artifacts?.pending_frame_embeddings ?? 0;
  const embeddingProcessed = embeddingProgress.processed ?? 0;
  const embeddingUpdated = embeddingProgress.updated ?? 0;
  const embeddingFailed = embeddingProgress.failed ?? 0;
  const embeddingRemaining = embeddingProgress.remaining ?? Math.max(embeddingPending - embeddingProcessed, 0);

  return (
    <>
      <Hero
        eyebrow="Drama Finder / Ingest"
        title="把入库流程收进独立页面，让检索入口保持轻量。"
        description="这里保留提交单集任务与轮询任务状态的完整闭环。切换页面不会改变后端契约，仍然沿用现有入库 API 和任务状态结构。"
        activePage="ingest"
        onNavigate={onNavigate}
      />

      <section className="ingest-grid grid grid-cols-1 lg:grid-cols-[1.08fr_0.92fr] gap-[18px]">
        <div className="stack grid gap-[18px]">
          <section className="panel">
            <h2 className="m-0 mb-4 text-xl font-bold">入库任务</h2>
            <div className="sub -mt-2 mb-[18px] text-muted text-[13px] leading-relaxed font-sans">
              先提交 `manifest + series_id + episode_id`，再用右侧状态卡轮询任务进度。
            </div>
            <div className="field-grid grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="md:col-span-2">
                <label htmlFor="manifestPath" className="block mb-1.5 text-muted text-xs font-sans">Manifest 路径</label>
                <input
                  id="manifestPath"
                  className="w-full"
                  value={manifestPath}
                  onChange={(e) => setManifestPath(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="seriesId" className="block mb-1.5 text-muted text-xs font-sans">Series ID</label>
                <input
                  id="seriesId"
                  className="w-full"
                  value={seriesId}
                  onChange={(e) => setSeriesId(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="episodeId" className="block mb-1.5 text-muted text-xs font-sans">Episode ID</label>
                <input
                  id="episodeId"
                  className="w-full"
                  value={episodeId}
                  onChange={(e) => setEpisodeId(e.target.value)}
                />
              </div>
            </div>
            <div className="actions flex gap-2.5 mt-3.5">
              <button
                type="button"
                className="primary"
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading ? '提交中...' : '提交入库'}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => pollJob()}
                disabled={loading}
              >
                {loading ? '刷新中...' : '刷新状态'}
              </button>
            </div>
          </section>
        </div>

        <div className="stack grid gap-[18px]">
          <section className="panel status-card grid gap-3">
            <h2 className="m-0 mb-4 text-xl font-bold">任务状态</h2>
            <div className="status-strip flex flex-wrap gap-2.5">
              <div className="pill px-3 py-2 rounded-full bg-white/90 border border-line text-xs font-sans">
                Job ID：<span className="text-muted">{job?.id || '未提交'}</span>
              </div>
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
            <div className="muted text-muted font-sans text-xs">
              processed {embeddingProcessed} / {embeddingPending} · updated {embeddingUpdated} · failed {embeddingFailed} · remaining {embeddingRemaining}
            </div>
            <div className="muted text-muted font-sans text-sm">
              {error ? (
                <span className="text-danger">{error}</span>
              ) : job ? (
                <span className={job.status === 'completed' ? 'text-success' : job.status === 'failed' ? 'text-danger' : ''}>
                  {job.error_message ? `错误：${job.error_message}` : '任务记录已更新。'}
                  {job.artifacts?.embedding_status && ` 图片向量状态：${job.artifacts.embedding_status}。`}
                </span>
              ) : (
                '提交任务后，这里会显示实时状态。'
              )}
            </div>
            <div className="json-box mt-2">
              {JSON.stringify(job || {}, null, 2)}
            </div>
          </section>
        </div>
      </section>
    </>
  );
};
