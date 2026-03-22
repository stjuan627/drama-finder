import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';

interface ImagePreviewProps {
  images: string[] | null;
  currentIndex: number;
  onNavigate: (index: number) => void;
  onClose: () => void;
}

export const ImagePreview: React.FC<ImagePreviewProps> = ({
  images,
  currentIndex,
  onNavigate,
  onClose,
}) => {
  const dialogRef = useRef<HTMLDivElement | null>(null);

  const safeIndex = useMemo(() => {
    if (!images || images.length === 0) {
      return 0;
    }
    return Math.min(Math.max(currentIndex, 0), images.length - 1);
  }, [currentIndex, images]);

  const canGoPrev = safeIndex > 0;
  const canGoNext = images ? safeIndex < images.length - 1 : false;

  const handlePrev = useCallback(() => {
    if (canGoPrev) {
      onNavigate(safeIndex - 1);
    }
  }, [canGoPrev, onNavigate, safeIndex]);

  const handleNext = useCallback(() => {
    if (canGoNext && images) {
      onNavigate(safeIndex + 1);
    }
  }, [canGoNext, images, onNavigate, safeIndex]);

  useEffect(() => {
    if (!images) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlePrev();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNext();
      } else if (e.key === 'Tab') {
        e.preventDefault();
        dialogRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    dialogRef.current?.focus();

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [images, onClose, handlePrev, handleNext]);

  if (!images || images.length === 0) return null;

  const currentSrc = images[safeIndex];

  return (
    <div
      ref={dialogRef}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-label="图片预览"
      tabIndex={-1}
    >
      <button
        type="button"
        className="absolute top-6 right-6 p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-full transition-all z-[110]"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        aria-label="关闭预览"
      >
        <X size={32} />
      </button>

      <div
        className="absolute top-6 left-1/2 -translate-x-1/2 px-4 py-1.5 bg-white/10 backdrop-blur-md rounded-full text-white/90 text-sm font-mono z-[110]"
        aria-live="polite"
      >
        {safeIndex + 1} / {images.length}
      </div>

      <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 flex justify-between px-4 md:px-8 pointer-events-none z-[110]">
        <button
          type="button"
          className="p-3 rounded-full bg-white/5 hover:bg-white/10 text-white transition-all pointer-events-auto disabled:opacity-20 disabled:cursor-not-allowed"
          onClick={(e) => {
            e.stopPropagation();
            handlePrev();
          }}
          disabled={!canGoPrev}
          aria-disabled={!canGoPrev}
          aria-label="上一张"
        >
          <ChevronLeft size={36} />
        </button>
        <button
          type="button"
          className="p-3 rounded-full bg-white/5 hover:bg-white/10 text-white transition-all pointer-events-auto disabled:opacity-20 disabled:cursor-not-allowed"
          onClick={(e) => {
            e.stopPropagation();
            handleNext();
          }}
          disabled={!canGoNext}
          aria-disabled={!canGoNext}
          aria-label="下一张"
        >
          <ChevronRight size={36} />
        </button>
      </div>
      
      <button
        type="button"
        className="relative w-full h-full p-4 md:p-12 flex items-center justify-center"
        onClick={(e) => e.stopPropagation()}
        aria-label="当前预览图片"
      >
        <img
          key={currentSrc}
          src={currentSrc}
          alt={`预览图 ${safeIndex + 1}`}
          className="max-w-full max-h-full object-contain shadow-2xl animate-in zoom-in-95 duration-300"
        />
      </button>
    </div>
  );
};
