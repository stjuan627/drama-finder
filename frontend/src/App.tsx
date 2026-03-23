import { useEffect, useState } from 'react';
import { Layout } from './components/Layout';
import { SearchPage } from './pages/SearchPage';
import { IngestPage } from './pages/IngestPage';

type Page = 'search' | 'ingest';

declare global {
  interface Window {
    __DRAMA_FINDER_PAGE__?: Page;
  }
}

function resolvePage(pathname: string): Page {
  if (pathname === '/ingest' || pathname === '/ui/ingest') {
    return 'ingest';
  }
  return 'search';
}

function nextPath(page: Page, pathname: string): string {
  if (pathname.startsWith('/ui/')) {
    return page === 'search' ? '/ui/search' : '/ui/ingest';
  }
  return page === 'search' ? '/search' : '/ingest';
}

function App() {
  const [activePage, setActivePage] = useState<Page>(() => {
    return window.__DRAMA_FINDER_PAGE__ ?? resolvePage(window.location.pathname);
  });

  useEffect(() => {
    const syncPage = () => {
      setActivePage(window.__DRAMA_FINDER_PAGE__ ?? resolvePage(window.location.pathname));
    };

    window.addEventListener('popstate', syncPage);
    syncPage();

    return () => {
      window.removeEventListener('popstate', syncPage);
    };
  }, []);

  const handleNavigate = (page: Page) => {
    setActivePage(page);
    window.__DRAMA_FINDER_PAGE__ = page;
    const newPath = nextPath(page, window.location.pathname);
    window.history.pushState({}, '', newPath);
  };

  return (
    <Layout activePage={activePage} onNavigate={handleNavigate}>
      {activePage === 'search' ? (
        <SearchPage />
      ) : (
        <IngestPage />
      )}
    </Layout>
  );
}

export default App;
