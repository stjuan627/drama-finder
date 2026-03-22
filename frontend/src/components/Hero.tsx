import React from 'react';

interface HeroProps {
  eyebrow: string;
  title: string;
  description: string;
  activePage: 'search' | 'ingest';
  onNavigate: (page: 'search' | 'ingest') => void;
}

export const Hero: React.FC<HeroProps> = ({
  eyebrow,
  title,
  description,
  activePage,
  onNavigate,
}) => {
  return (
    <section className="hero relative overflow-hidden p-7 pb-[30px] border border-line rounded-[28px] bg-gradient-to-br from-white/86 to-[#fff5e6]/76 shadow-custom">
      <div className="relative z-[1]">
        <div className="eyebrow mb-3 text-accent tracking-[0.16em] uppercase font-sans text-[12px]">
          {eyebrow}
        </div>
        <h1 className="m-0 max-w-[760px] leading-[1.06] text-[clamp(34px,6vw,64px)] font-bold">
          {title}
        </h1>
        <p className="mt-[18px] max-w-[720px] text-muted leading-relaxed text-[15px] font-sans">
          {description}
        </p>
        <div className="hero-cta mt-5 flex flex-wrap gap-2.5">
          <button
            type="button"
            className={`nav-link ${activePage === 'search' ? 'active' : ''}`}
            onClick={() => onNavigate('search')}
          >
            进入检索
          </button>
          <button
            type="button"
            className={`nav-link ${activePage === 'ingest' ? 'active' : ''}`}
            onClick={() => onNavigate('ingest')}
          >
            {activePage === 'ingest' ? '当前是入库页' : '切换到入库'}
          </button>
        </div>
      </div>
      <div
        className="pointer-events-none absolute -right-[70px] -top-[110px] h-[260px] w-[260px] rounded-full opacity-20"
        style={{ background: 'radial-gradient(circle, rgba(158,79,43,0.14), transparent 68%)' }}
      />
      <div
        className="pointer-events-none absolute -bottom-[110px] -left-[80px] h-[220px] w-[220px] rounded-full opacity-20"
        style={{ background: 'radial-gradient(circle, rgba(158,79,43,0.14), transparent 68%)' }}
      />
    </section>
  );
};
