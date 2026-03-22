import React, { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../api/api';
import { SearchResponse } from '../types/api';
import { ImagePreview } from '../components/ImagePreview';

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '检索失败，请稍后再试。';
}

type SearchMode = 'text' | 'image';

export const SearchPage: React.FC = () => {
  const [searchMode, setSearchMode] = useState<SearchMode>('text');
  const [queryText, setQueryText] = useState('皇上驾到');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewState, setPreviewState] = useState<{ images: string[]; index: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewTriggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    return () => {
      if (imagePreviewUrl) {
        URL.revokeObjectURL(imagePreviewUrl);
      }
    };
  }, [imagePreviewUrl]);

  const handleFileChange = useCallback((file: File | null) => {
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
    }
    if (file) {
      setImageFile(file);
      setImagePreviewUrl(URL.createObjectURL(file));
    } else {
      setImageFile(null);
      setImagePreviewUrl(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }, [imagePreviewUrl]);

  const applyPastedImage = useCallback((items: DataTransferItemList | undefined | null) => {
    if (!items) {
      return false;
    }

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith('image/')) {
        const file = items[i].getAsFile();
        if (file) {
          handleFileChange(file);
          return true;
        }
      }
    }

    return false;
  }, [handleFileChange]);

  const handlePaste = (e: React.ClipboardEvent) => {
    if (applyPastedImage(e.clipboardData?.items)) {
      e.preventDefault();
    }
  };

  useEffect(() => {
    if (searchMode !== 'image') {
      return undefined;
    }

    const handleWindowPaste = (event: ClipboardEvent) => {
      if (applyPastedImage(event.clipboardData?.items)) {
        event.preventDefault();
      }
    };

    window.addEventListener('paste', handleWindowPaste);
    return () => {
      window.removeEventListener('paste', handleWindowPaste);
    };
  }, [applyPastedImage, searchMode]);

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
    if (!imageFile) {
      setError('请先选择或粘贴截图文件。');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchImage(imageFile);
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
      <section className="search-shell grid gap-[18px]">
        <section className="panel search-grid grid grid-cols-1 gap-[18px] items-start">
          <div className="search-form grid gap-4">
            <div className="tabs" role="tablist" aria-label="选择检索模式">
              <button
                type="button"
                className={`tab-btn ${searchMode === 'text' ? 'active' : ''}`}
                onClick={() => {
                  setError(null);
                  setSearchMode('text');
                }}
                role="tab"
                id="search-tab-text"
                aria-selected={searchMode === 'text'}
                aria-controls="search-panel-text"
              >
                文搜
              </button>
              <button
                type="button"
                className={`tab-btn ${searchMode === 'image' ? 'active' : ''}`}
                onClick={() => {
                  setError(null);
                  setSearchMode('image');
                }}
                role="tab"
                id="search-tab-image"
                aria-selected={searchMode === 'image'}
                aria-controls="search-panel-image"
              >
                图搜
              </button>
            </div>

            {searchMode === 'text' ? (
              <div
                className="grid gap-4"
                role="tabpanel"
                id="search-panel-text"
                aria-labelledby="search-tab-text"
              >
                <textarea
                  id="queryText"
                  aria-label="台词文本检索"
                  className="w-full min-h-[124px] resize-vertical"
                  placeholder="输入一句台词，如：皇上驾到"
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                />
                <div className="flex justify-end">
                  <button
                    type="button"
                    className="primary w-full md:w-auto"
                    onClick={handleTextSearch}
                    disabled={loading}
                  >
                    {loading ? '检索中...' : '开始检索'}
                  </button>
                </div>
              </div>
            ) : (
              <div
                className="grid gap-4"
                role="tabpanel"
                id="search-panel-image"
                aria-labelledby="search-tab-image"
              >
                <button
                  type="button"
                  className={`drop-zone ${imagePreviewUrl ? 'has-image' : ''}`}
                  onClick={() => fileInputRef.current?.click()}
                  onPaste={handlePaste}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const file = e.dataTransfer.files[0];
                    if (file && file.type.startsWith('image/')) {
                      handleFileChange(file);
                    }
                  }}
                  aria-label="上传或粘贴图片"
                >
                  <input
                    id="imageFile"
                    type="file"
                    accept="image/*"
                    className="hidden"
                    ref={fileInputRef}
                    onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                  />
                  {imagePreviewUrl ? (
                    <div className="image-preview-container">
                      <img src={imagePreviewUrl} alt="待检索截图预览" />
                    </div>
                  ) : (
                    <div className="text-center py-4 image-upload-empty">
                      <div className="text-accent text-lg mb-1">点击上传 或 粘贴图片</div>
                      <div className="text-muted text-xs">支持拖拽图片文件到此处</div>
                    </div>
                  )}
                </button>
                <div className="image-upload-actions">
                  {imagePreviewUrl && (
                    <button
                      type="button"
                      className="remove-image-btn"
                      onClick={() => handleFileChange(null)}
                      title="移除图片"
                      aria-label="移除图片"
                    >
                      移除图片
                    </button>
                  )}
                </div>
                <div className="flex justify-end">
                  <button
                    type="button"
                    className="primary w-full md:w-auto"
                    onClick={handleImageSearch}
                    disabled={loading || !imageFile}
                  >
                    {loading ? '检索中...' : '开始检索'}
                  </button>
                </div>
              </div>
            )}
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
