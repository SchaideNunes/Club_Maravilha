import React from 'react';

interface LogoProps {
  className?: string;
  variant?: 'light' | 'dark'; // light: for dark/colored backgrounds (white text), dark: for white backgrounds (navy text)
  size?: 'sm' | 'md' | 'lg';
}

export const ClubeMaravilhaLogo: React.FC<LogoProps> = ({
  className = '',
  variant = 'light',
  size = 'md'
}) => {
  const textColor = variant === 'light' ? '#FFFFFF' : '#1F3347';
  const scale = size === 'sm' ? 'h-8' : size === 'lg' ? 'h-16' : 'h-12';

  return (
    <div className={`flex flex-col items-center select-none ${className}`}>
      {/* Golden Sun & Waves Graphic */}
      <svg
        viewBox="0 0 100 55"
        className={`${scale} w-auto`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Sun Disk & Rays */}
        <circle cx="50" cy="28" r="13" fill="#EAA43B" />
        
        {/* Radiating Sun Rays */}
        <path d="M50 4V10" stroke="#EAA43B" strokeWidth="3" strokeLinecap="round" />
        <path d="M33 11L37 15.5" stroke="#EAA43B" strokeWidth="3" strokeLinecap="round" />
        <path d="M67 11L63 15.5" stroke="#EAA43B" strokeWidth="3" strokeLinecap="round" />
        <path d="M21 24L27 26" stroke="#EAA43B" strokeWidth="3" strokeLinecap="round" />
        <path d="M79 24L73 26" stroke="#EAA43B" strokeWidth="3" strokeLinecap="round" />

        {/* Ocean / River Waves Arc (Curved stylized lines) */}
        <path
          d="M15 42C28 35 38 45 52 39C64 34 76 43 85 41"
          stroke={variant === 'light' ? '#FFFFFF' : '#1F3347'}
          strokeWidth="3.5"
          strokeLinecap="round"
        />
        <path
          d="M22 49C33 44 42 51 55 46C66 42 75 49 82 48"
          stroke="#EAA43B"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>

      {/* Brand Typographic Wordmark */}
      <div className="text-center font-extrabold tracking-wider leading-none mt-1">
        <div style={{ color: textColor }} className="text-[11px] sm:text-[13px] tracking-[0.18em]">
          CLUBE
        </div>
        <div style={{ color: textColor }} className="text-[13px] sm:text-[15px] tracking-[0.15em]">
          MARAVILHA
        </div>
      </div>
    </div>
  );
};
