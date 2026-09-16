import { useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { HeroSection } from './components/landing/HeroSection';
import { SportsProgrammingSection } from './components/landing/SportsProgrammingSection';
import { LeisureProgrammingSection } from './components/landing/LeisureProgrammingSection';
import { ExperiencesSection } from './components/landing/ExperiencesSection';
import { AboutBannerSection } from './components/landing/AboutBannerSection';
import { MemberPortalModal } from './components/portal/MemberPortalModal';
import { Footer } from './components/layout/Footer';

export default function App() {
  const [isPortalOpen, setIsPortalOpen] = useState(false);
  const [selectedCourtForBooking, setSelectedCourtForBooking] = useState<string | undefined>(undefined);

  const handleOpenPortal = (courtOrEventName?: string) => {
    setSelectedCourtForBooking(courtOrEventName);
    setIsPortalOpen(true);
  };

  const handleNavigateSection = (sectionId: string) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#1F3347] font-sans selection:bg-amber-400 selection:text-slate-900">
      {/* 1. Header Oficial com Paleta Steel Blue (#4E7A9C) e Logo do Sol Dourado */}
      <Navbar 
        onOpenPortal={() => handleOpenPortal()}
        onNavigateSection={handleNavigateSection}
      />

      {/* 2. Banner Hero Principal (Homepage.png) com Card Flutuante 'QUERO SER SÓCIO' */}
      <HeroSection 
        onOpenPortal={() => handleOpenPortal()}
        onExploreProgramming={() => handleNavigateSection('programacao-esportes')}
      />

      {/* 3. Programação Esportes (Vôlei, Futsal com Badges de Data e Botões Saiba Mais) */}
      <SportsProgrammingSection 
        onSelectEvent={(eventTitle) => handleOpenPortal(eventTitle)}
        onViewFullSchedule={() => handleNavigateSection('programacao-esportes')}
      />

      {/* 4. Programação Lazer (Shows: João Gomes, Calypso, Dorgival, Tarcísio) */}
      <LeisureProgrammingSection 
        onSelectShow={(showTitle) => handleOpenPortal(showTitle)}
        onViewFullSchedule={() => handleNavigateSection('programacao-lazer')}
      />

      {/* 5. Seção de EXPERIÊNCIAS (3 Cards Azuis com Ícones de Halter, Apito, Óculos e Botões Dourados) */}
      <ExperiencesSection 
        onSelectExperience={(exp) => handleOpenPortal(exp)}
        onViewFullSchedule={() => handleNavigateSection('programacao-esportes')}
      />

      {/* 6. Banner Institucional 'Tradição, esporte e convivência em um só lugar' (Família / Teofilândia) */}
      <AboutBannerSection 
        onExploreClub={() => handleOpenPortal()}
      />

      {/* 7. Rodapé Steel Blue (#4E7A9C) com Contatos de Teofilândia e Redes Sociais */}
      <Footer 
        onOpenPortal={() => handleOpenPortal()}
        onNavigateSection={handleNavigateSection}
      />

      {/* 8. Portal Interativo do Associado (Quadras, Pix e Convidados integrados à API) */}
      <MemberPortalModal
        isOpen={isPortalOpen}
        onClose={() => setIsPortalOpen(false)}
        preSelectedCourt={selectedCourtForBooking}
      />
    </div>
  );
}
