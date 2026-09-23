import React from 'react';
import logoImg from '../../assets/logo.png';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'light' | 'dark' | 'default';
}

export const ClubeMaravilhaLogo: React.FC<LogoProps> = ({
  className = '',
  size = 'md',
  variant = 'default'
}) => {
  const heightClass = size === 'sm' ? 'h-9' : size === 'lg' ? 'h-20' : 'h-12';
  const filterClass = variant === 'light' 
    ? 'drop-shadow-[0_1px_3px_rgba(255,255,255,0.7)]' 
    : '';

  return (
    <div className={`inline-flex items-center select-none ${className}`}>
      <img
        src={logoImg}
        alt="Clube Maravilha"
        className={`${heightClass} w-auto object-contain transition-transform duration-200 hover:scale-105 ${filterClass}`}
      />
    </div>
  );
};
