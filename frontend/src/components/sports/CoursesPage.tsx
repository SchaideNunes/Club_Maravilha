import React from 'react';
import { CategoryHeroBanner } from '../common/CategoryHeroBanner';
import { ModalitiesGrid, ModalityItem } from './ModalitiesGrid';
import { ClassScheduleSection } from './ClassScheduleSection';

import heroCoachImg from '../../assets/courses_hero_coach.jpg';
import soccerImg from '../../assets/sports_soccer.jpg';
import voleiImg from '../../assets/sports_volei.jpg';
import futsalImg from '../../assets/sports_futsal.jpg';
import swimmingImg from '../../assets/sports_swimming.jpg';

interface CoursesPageProps {
  onOpenPortal: (className?: string) => void;
}

export const CoursesPage: React.FC<CoursesPageProps> = ({ onOpenPortal }) => {
  const courseModalities: ModalityItem[] = [
    {
      id: 'curso-futebol',
      title: 'Futebol',
      imageSrc: soccerImg
    },
    {
      id: 'curso-volei',
      title: 'Vôlei',
      imageSrc: voleiImg
    },
    {
      id: 'curso-futsal',
      title: 'Futsal',
      imageSrc: futsalImg
    },
    {
      id: 'curso-natacao',
      title: 'Natação',
      imageSrc: swimmingImg
    }
  ];

  return (
    <div className="pb-16">
      {/* Hero Section */}
      <CategoryHeroBanner
        title="Cursos Esportivos"
        subtitle="Mais que esporte: treino para a vida."
        imageSrc={heroCoachImg}
        imageAlt="Instrutor e alunos em aula esportiva no Clube Maravilha"
      />

      {/* Cursos Esportivos Grid */}
      <ModalitiesGrid
        sectionTitle="Cursos Esportivos"
        modalities={courseModalities}
        onSelectModality={(title) => onOpenPortal(`Inscrição Curso de ${title}`)}
      />

      {/* Programação Aulas */}
      <ClassScheduleSection
        onSelectClass={(classTitle) => onOpenPortal(`Aula de ${classTitle}`)}
        onViewFullSchedule={() => onOpenPortal('Grade Completa de Aulas')}
      />
    </div>
  );
};
