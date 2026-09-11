import { useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { HeroSection } from './components/landing/HeroSection';
import { FacilitiesSection } from './components/landing/FacilitiesSection';
import { TechnologySection } from './components/landing/TechnologySection';
import { MemberPortalModal } from './components/portal/MemberPortalModal';
import { Footer } from './components/layout/Footer';

export default function App() {
  const [isPortalOpen, setIsPortalOpen] = useState(false);
  const [selectedCourtForBooking, setSelectedCourtForBooking] = useState<string | undefined>(undefined);

  const handleOpenPortal = (courtName?: string) => {
    setSelectedCourtForBooking(courtName);
    setIsPortalOpen(true);
  };

  const handleNavigateSection = (sectionId: string) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-amber-400 selection:text-slate-950">
      {/* Header com Efeito Vidro & Menu Lateral 30% */}
      <Navbar 
        onOpenPortal={() => handleOpenPortal()}
        onNavigateSection={handleNavigateSection}
      />

      {/* Hero Section Imersivo: Homepage.png + CLUB MARAVILHA em Destaque */}
      <HeroSection 
        onOpenPortal={() => handleOpenPortal()}
        onExploreFacilities={() => handleNavigateSection('facilities')}
      />

      {/* Complexo Esportivo & Instalações: Image1.png + Quadras */}
      <FacilitiesSection 
        onSelectCourtForBooking={(courtName) => handleOpenPortal(courtName)}
      />

      {/* Tecnologia, Catraca Facial, Pix em 2s & Franquia de 8 Convidados */}
      <TechnologySection 
        onOpenPortal={() => handleOpenPortal()}
      />

      {/* Rodapé do Clube */}
      <Footer 
        onOpenPortal={() => handleOpenPortal()}
        onNavigateSection={handleNavigateSection}
      />

      {/* Modal / Painel Interativo do Associado */}
      <MemberPortalModal
        isOpen={isPortalOpen}
        onClose={() => setIsPortalOpen(false)}
        preSelectedCourt={selectedCourtForBooking}
      />
    </div>
  );
}
