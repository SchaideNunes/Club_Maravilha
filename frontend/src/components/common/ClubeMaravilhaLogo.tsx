import React from 'react';
import logoImg from '../../assets/logo.png';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'light' | 'dark' | 'default' | 'on-blue';
}

export const ClubeMaravilhaLogo: React.FC<LogoProps> = ({
  className = '',
  size = 'md',
  variant = 'default'
}) => {
  const heightClass = size === 'sm' ? 'h-9' : size === 'lg' ? 'h-20' : 'h-14';
  const filterClass =
    variant === 'light' || variant === 'on-blue'
      ? 'drop-shadow-[0_1px_2px_rgba(255,255,255,0.95)] drop-shadow-[0_0_1px_rgba(255,255,255,1)]'
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
