import { useState, useEffect } from 'react';
import { Navbar, PageRoute } from './components/layout/Navbar';
import { HeroSection } from './components/landing/HeroSection';
import { SportsProgrammingSection } from './components/landing/SportsProgrammingSection';
import { LeisureProgrammingSection } from './components/landing/LeisureProgrammingSection';
import { ExperiencesSection } from './components/landing/ExperiencesSection';
import { AboutBannerSection } from './components/landing/AboutBannerSection';
import { MemberPortalModal } from './components/portal/MemberPortalModal';
import { Footer } from './components/layout/Footer';

// Subpages
import { SportsPage } from './components/sports/SportsPage';
import { CoursesPage } from './components/sports/CoursesPage';
import { LeisurePage } from './components/leisure/LeisurePage';
import { UserDashboardPage } from './components/user/UserDashboardPage';

export default function App() {
  const [currentPage, setCurrentPage] = useState<PageRoute>('home');
  const [isPortalOpen, setIsPortalOpen] = useState(false);
  const [selectedCourtForBooking, setSelectedCourtForBooking] = useState<string | undefined>(undefined);

  // Synchronize route with URL hash on load and hashchange
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.toLowerCase();
      if (hash.includes('esporte')) {
        setCurrentPage('esportes');
      } else if (hash.includes('curso') || hash.includes('educacao')) {
        setCurrentPage('cursos-esportivos');
      } else if (hash.includes('lazer')) {
        setCurrentPage('lazer');
      } else if (hash.includes('usuario') || hash.includes('associado')) {
        setCurrentPage('usuario');
      } else {
        setCurrentPage('home');
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateToPage = (page: PageRoute) => {
    setCurrentPage(page);
    if (page === 'home') {
      window.location.hash = '#/';
    } else {
      window.location.hash = `#/${page}`;
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenPortal = (courtOrEventName?: string) => {
    setSelectedCourtForBooking(courtOrEventName);
    setIsPortalOpen(true);
  };

  const handleNavigateSection = (sectionId: string) => {
    if (currentPage !== 'home') {
      navigateToPage('home');
      setTimeout(() => {
        const el = document.getElementById(sectionId);
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } else {
      const el = document.getElementById(sectionId);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleSelectExperience = (experienceName: string) => {
    if (experienceName.toLowerCase().includes('curso')) {
      navigateToPage('cursos-esportivos');
    } else if (experienceName.toLowerCase().includes('esporte')) {
      navigateToPage('esportes');
    } else if (experienceName.toLowerCase().includes('lazer')) {
      navigateToPage('lazer');
    } else {
      handleOpenPortal(experienceName);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#1F3347] font-sans selection:bg-amber-400 selection:text-slate-900">
      {/* Rota Especial: Página do Usuário / Dashboard do Associado */}
      {currentPage === 'usuario' ? (
        <UserDashboardPage
          onBackToHome={() => navigateToPage('home')}
          onNavigatePage={navigateToPage}
          onOpenBookingModal={(court) => handleOpenPortal(court)}
          onOpenPaymentModal={() => handleOpenPortal()}
        />
      ) : (
        <>
          {/* Header Oficial com Steel Blue (#4E7A9C) e Logo */}
          <Navbar
            currentPage={currentPage}
            onNavigatePage={navigateToPage}
            onOpenPortal={() => handleOpenPortal()}
            onNavigateSection={handleNavigateSection}
          />

          {/* Rota 1: Home / Landing Page Principal */}
          {currentPage === 'home' && (
            <main>
              <HeroSection
                onOpenPortal={() => handleOpenPortal()}
                onExploreProgramming={() => handleNavigateSection('programacao-esportes')}
              />

              <SportsProgrammingSection
                onSelectEvent={(eventTitle) => handleOpenPortal(eventTitle)}
                onViewFullSchedule={() => navigateToPage('esportes')}
              />

              <LeisureProgrammingSection
                onSelectShow={(showTitle) => handleOpenPortal(showTitle)}
                onViewFullSchedule={() => navigateToPage('lazer')}
              />

              <ExperiencesSection
                onSelectExperience={handleSelectExperience}
                onViewFullSchedule={() => navigateToPage('esportes')}
              />

              <AboutBannerSection onExploreClub={() => handleOpenPortal()} />
            </main>
          )}

          {/* Rota 2: Página de Esportes */}
          {currentPage === 'esportes' && (
            <main>
              <SportsPage onOpenPortal={(court) => handleOpenPortal(court)} />
            </main>
          )}

          {/* Rota 3: Página de Cursos Esportivos / Educação */}
          {currentPage === 'cursos-esportivos' && (
            <main>
              <CoursesPage onOpenPortal={(cls) => handleOpenPortal(cls)} />
            </main>
          )}

          {/* Rota 4: Página de Lazer */}
          {currentPage === 'lazer' && (
            <main>
              <LeisurePage onOpenPortal={(show) => handleOpenPortal(show)} />
            </main>
          )}

          {/* Rodapé Oficial Steel Blue (#4E7A9C) */}
          <Footer
            onOpenPortal={() => handleOpenPortal()}
            onNavigateSection={handleNavigateSection}
          />
        </>
      )}

      {/* Modal Interativo do Associado (Quadras, Pix e Convidados integrados à API) */}
      <MemberPortalModal
        isOpen={isPortalOpen}
        onClose={() => setIsPortalOpen(false)}
        preSelectedCourt={selectedCourtForBooking}
      />
    </div>
  );
}

