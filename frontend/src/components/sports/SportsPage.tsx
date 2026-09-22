import React from 'react';
import { CategoryHeroBanner } from '../common/CategoryHeroBanner';
import { ModalitiesGrid, ModalityItem } from './ModalitiesGrid';
import { SportsProgrammingSection } from '../landing/SportsProgrammingSection';

import heroVolleyballImg from '../../assets/sports_hero_volleyball.jpg';
import voleiImg from '../../assets/sports_volei.jpg';
import futsalImg from '../../assets/sports_futsal.jpg';
import swimmingImg from '../../assets/sports_swimming.jpg';
import soccerImg from '../../assets/sports_soccer.jpg';

interface SportsPageProps {
  onOpenPortal: (courtOrEventName?: string) => void;
}

export const SportsPage: React.FC<SportsPageProps> = ({ onOpenPortal }) => {
  const sportsModalities: ModalityItem[] = [
    {
      id: 'mod-volei',
      title: 'Vôlei',
      imageSrc: voleiImg
    },
    {
      id: 'mod-futsal',
      title: 'Futsal',
      imageSrc: futsalImg
    },
    {
      id: 'mod-natacao',
      title: 'Natação',
      imageSrc: swimmingImg
    },
    {
      id: 'mod-futebol',
      title: 'Futebol',
      imageSrc: soccerImg
    }
  ];

  return (
    <div className="pb-16">
      {/* Hero Section */}
      <CategoryHeroBanner
        title="Esportes"
        subtitle="Mais que esporte: treino para a vida."
        imageSrc={heroVolleyballImg}
        imageAlt="Partida de vôlei feminino no Clube Maravilha"
      />

      {/* Modalidades Grid */}
      <ModalitiesGrid
        sectionTitle="Modalidades"
        modalities={sportsModalities}
        onSelectModality={(title) => onOpenPortal(title)}
      />

      {/* Programação Esportes */}
      <SportsProgrammingSection
        onSelectEvent={(eventTitle) => onOpenPortal(eventTitle)}
        onViewFullSchedule={() => onOpenPortal('Quadra Poliesportiva')}
      />
    </div>
  );
};
