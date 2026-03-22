import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
  activePage: 'search' | 'ingest';
  onNavigate: (page: 'search' | 'ingest') => void;
}

export const Layout: React.FC<LayoutProps> = ({ children, activePage, onNavigate }) => {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="topbar sticky top-0 z-10 backdrop-blur-lg bg-white/75 border-b border-line">
        <div className="topbar-inner max-w-[1180px] mx-auto px-4 py-3.5 flex items-center justify-between gap-4">
          <div className="brand grid gap-0.5">
            <div className="brand-mark font-sans text-[12px] tracking-[0.18em] uppercase text-accent">
              Drama Finder
            </div>
            <div className="brand-title text-lg font-bold">
              一句台词，一张截图，找到剧集。
            </div>
          </div>
          <nav className="nav flex flex-wrap gap-2.5">
            <button
              type="button"
              className={`nav-link ${activePage === 'search' ? 'active' : ''}`}
              onClick={() => onNavigate('search')}
            >
              检索
            </button>
            <button
              type="button"
              className={`nav-link ${activePage === 'ingest' ? 'active' : ''}`}
              onClick={() => onNavigate('ingest')}
            >
              入库
            </button>
          </nav>
        </div>
      </header>
      <main className="page max-w-[1180px] mx-auto px-4 my-7 mb-12 grid gap-[18px] w-full">
        {children}
      </main>
    </div>
  );
};
