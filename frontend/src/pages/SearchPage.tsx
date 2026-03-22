import React, { useState, useRef } from 'react';
import { Hero } from '../components/Hero';
import { api } from '../api/api';
import { SearchResponse } from '../types/api';
import { ImagePreview } from '../components/ImagePreview';

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '检索失败，请稍后再试。';
}

interface SearchPageProps {
  onNavigate: (page: 'search' | 'ingest') => void;
}

export const SearchPage: React.FC<SearchPageProps> = ({ onNavigate }) => {
  const [queryText, setQueryText] = useState('皇上驾到');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewState, setPreviewState] = useState<{ images: string[]; index: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewTriggerRef = useRef<HTMLButtonElement | null>(null);

  const secondsToLabel = (value: number) => {
    const total = Math.max(0, Math.floor(value || 0));
    const hh = String(Math.floor(total / 3600)).padStart(2, '0');
    const mm = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
    const ss = String(total % 60).padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  };

  const handleTextSearch = async () => {
    if (!queryText.trim()) {
      setError('请输入台词文本。');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchText({ query: queryText.trim(), limit: 5 });
      setResults(data);
    } catch (error: unknown) {
      setError(getErrorMessage(error));
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const handleImageSearch = async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setError('请先选择截图文件。');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchImage(file);
      setResults(data);
    } catch (error: unknown) {
      setError(getErrorMessage(error));
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const openPreview = (
    images: string[],
    index: number,
    trigger: HTMLButtonElement | null,
  ) => {
    previewTriggerRef.current = trigger;
    setPreviewState({ images, index });
  };

  const closePreview = () => {
    setPreviewState(null);
    previewTriggerRef.current?.focus();
  };

  return (
    <>
      <Hero
        eyebrow="Drama Finder / Search"
        title="默认进入检索，把线索压缩成一张图或一句台词。"
        description="当前 demo 已拆成检索页与入库页。这里优先承载日常查询：顶部输入线索，下面直接查看候选区间、置信度、文本证据，以及可附带的关联截图。"
        activePage="search"
        onNavigate={onNavigate}
      />

      <section className="search-shell grid gap-[18px]">
        <section className="panel search-grid grid grid-cols-1 lg:grid-cols-[1.45fr_0.95fr] gap-[18px] items-start">
          <div className="search-form grid gap-4">
            <div>
              <h2 className="m-0 mb-4 text-xl font-bold">常规搜索框</h2>
              <div className="sub -mt-2 mb-[18px] text-muted text-[13px] leading-relaxed font-sans">
                文本检索作为主入口，截图检索作为补充入口；两种方式都会把结果落到下方统一列表。
              </div>
            </div>
            <div>
              <label htmlFor="queryText" className="block mb-1.5 text-muted text-xs font-sans">台词文本</label>
              <textarea
                id="queryText"
                className="w-full min-h-[124px] resize-vertical"
                placeholder="例如：皇上驾到"
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
              />
            </div>
            <div className="search-actions grid grid-cols-1 md:grid-cols-[1fr_220px] gap-3 items-end">
              <div>
                <label htmlFor="imageFile" className="block mb-1.5 text-muted text-xs font-sans">关联截图（可选）</label>
                <input
                  id="imageFile"
                  type="file"
                  accept="image/*"
                  className="w-full"
                  ref={fileInputRef}
                />
              </div>
              <button
                type="button"
                className="primary"
                onClick={handleTextSearch}
                disabled={loading}
              >
                {loading ? '检索中...' : '开始文本检索'}
              </button>
            </div>
            <div className="actions flex gap-2.5 mt-3.5">
              <button
                type="button"
                className="secondary w-full md:w-auto"
                onClick={handleImageSearch}
                disabled={loading}
              >
                仅用截图检索
              </button>
            </div>
          </div>

          <div className="search-hint-grid grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-2.5">
            <div className="hint-card p-4 rounded-[18px] bg-white/60 border border-line">
              <strong className="block mb-1.5 text-sm font-bold">默认检索页</strong>
              <span className="text-muted text-xs leading-relaxed font-sans">
                打开 demo 就落到查询流程，避免被入库表单分散注意力。
              </span>
            </div>
            <div className="hint-card p-4 rounded-[18px] bg-white/60 border border-line">
              <strong className="block mb-1.5 text-sm font-bold">结果附图</strong>
              <span className="text-muted text-xs leading-relaxed font-sans">
                命中结果可展示关联截图；若图片暂不可直连，也会保留路径证据。
              </span>
            </div>
            <div className="hint-card p-4 rounded-[18px] bg-white/60 border border-line">
              <strong className="block mb-1.5 text-sm font-bold">区间优先</strong>
              <span className="text-muted text-xs leading-relaxed font-sans">
                仍以 `剧集 + 时间区间` 为主结果，截图与文本只作为证据补充。
              </span>
            </div>
          </div>
        </section>

        <section className="panel results-panel grid gap-4">
          <div>
            <h2 className="m-0 mb-4 text-xl font-bold">结果列表</h2>
            <div className="muted text-muted font-sans text-sm">
              {error ? (
                <span className="text-danger">{error}</span>
              ) : results ? (
                <>
                  检索完成 · low_confidence = <strong>{String(results.low_confidence)}</strong> · hits = <strong>{results.hits.length}</strong>
                </>
              ) : (
                '尚未执行检索。'
              )}
            </div>
          </div>
          <div className="results grid gap-3.5 min-h-[52px]">
            {results?.hits.length === 0 && (
              <div className="results-empty p-4 rounded-[18px] bg-white/70 border border-dashed border-line text-muted font-sans leading-relaxed">
                没有命中候选。若这是新剧集，可先去入库页补录对应剧集后再回来检索。
              </div>
            )}
            {results?.hits.map((hit) => (
              <article
                key={`${hit.series_id}-${hit.episode_id}-${hit.matched_start_ts}`}
                className="hit"
              >
                <div className="hit-head flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
                  <div className="hit-title text-lg font-bold flex items-center flex-wrap gap-2">
                    <span>{hit.series_id} / {hit.episode_id}</span>
                    <span className="hit-time-range font-mono text-accent bg-accent-soft/20 px-2.5 py-0.5 rounded-lg text-sm font-semibold">
                      {secondsToLabel(hit.matched_start_ts)} - {secondsToLabel(hit.matched_end_ts)}
                    </span>
                  </div>
                  <div className="score text-accent text-[13px] font-sans opacity-80 whitespace-nowrap">
                    score {hit.score.toFixed(4)}
                  </div>
                </div>
                
                <div className="evidence-text text-[15px] leading-relaxed p-3 px-4 bg-white/50 rounded-xl border-l-4 border-accent-soft">
                  {hit.evidence_text.length > 0 ? hit.evidence_text.join(' | ') : '（无文本证据）'}
                </div>

                <div className="hit-images-container mt-1">
                  {hit.evidence_images.length > 0 ? (
                    <div className="hit-images-list flex gap-3 overflow-x-auto py-1 pb-2">
                      {hit.evidence_images.map((path, index) => {
                        const imageUrl = api.getEvidenceUrl(path);
                        const allUrls = hit.evidence_images.map((imagePath) => api.getEvidenceUrl(imagePath));
                        return (
                          <button
                            key={path}
                            type="button"
                            className="hit-image-item flex-none w-[200px] aspect-video rounded-xl overflow-hidden border border-line bg-white shadow-sm cursor-zoom-in hover:ring-2 hover:ring-accent/30 transition-all text-left"
                            style={{
                              contentVisibility: 'auto',
                              containIntrinsicSize: '200px 112px',
                            }}
                            onClick={(event) => openPreview(allUrls, index, event.currentTarget)}
                            aria-label={`查看大图（第 ${index + 1} 张，共 ${allUrls.length} 张）`}
                          >
                            <img
                              src={imageUrl}
                              alt="证据截图"
                              loading="lazy"
                              decoding="async"
                              className="w-full h-full object-cover block"
                              onError={(e) => {
                                (e.target as HTMLImageElement).parentElement!.style.display = 'none';
                              }}
                            />
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="hit-images-empty text-[13px] text-muted p-3 bg-white/30 rounded-xl border border-dashed border-line flex items-center gap-2">
                      暂无关联截图证据
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      </section>

      <ImagePreview 
        images={previewState?.images ?? null}
        currentIndex={previewState?.index ?? 0}
        onNavigate={(index) => {
          setPreviewState((current) => (current ? { ...current, index } : current));
        }}
        onClose={closePreview}
      />
    </>
  );
};
