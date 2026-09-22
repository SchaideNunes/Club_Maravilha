import React from 'react';
import { CategoryHeroBanner } from '../common/CategoryHeroBanner';
import { LeisureActivitiesSection } from './LeisureActivitiesSection';
import { LeisureProgrammingSection } from '../landing/LeisureProgrammingSection';

import heroPoolImg from '../../assets/leisure_hero_pool.jpg';

interface LeisurePageProps {
  onOpenPortal: (showOrEventName?: string) => void;
}

export const LeisurePage: React.FC<LeisurePageProps> = ({ onOpenPortal }) => {
  return (
    <div className="pb-16">
      {/* Hero Section */}
      <CategoryHeroBanner
        title="Lazer"
        subtitle="Mais que esporte: treino para a vida."
        imageSrc={heroPoolImg}
        imageAlt="Momentos de lazer e piscina com amigos no Clube Maravilha"
      />

      {/* Atividades de Lazer (Entretenimento e Eventos) */}
      <LeisureActivitiesSection
        onSelectActivity={(title) => onOpenPortal(`Atividade: ${title}`)}
      />

      {/* Programação Lazer (Shows: João Gomes, Calypso, Dorgival, Tarcísio) */}
      <LeisureProgrammingSection
        onSelectShow={(showTitle) => onOpenPortal(showTitle)}
        onViewFullSchedule={() => onOpenPortal('Ingressos Shows')}
      />
    </div>
  );
};
