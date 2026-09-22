import React from 'react';

interface CategoryHeroBannerProps {
  title: string;
  subtitle?: string;
  imageSrc: string;
  imageAlt: string;
}

export const CategoryHeroBanner: React.FC<CategoryHeroBannerProps> = ({
  title,
  subtitle = 'Mais que esporte: treino para a vida.',
  imageSrc,
  imageAlt
}) => {
  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-6">
      <div className="flex flex-col md:flex-row items-center md:items-start gap-8 lg:gap-14">
        {/* Left Side: Large Rounded Hero Image */}
        <div className="w-full md:w-1/2 flex justify-center md:justify-start">
          <div className="relative w-full max-w-xl h-[260px] sm:h-[340px] md:h-[380px] rounded-3xl overflow-hidden shadow-lg shadow-slate-900/10 border border-slate-100">
            <img
              src={imageSrc}
              alt={imageAlt}
              className="w-full h-full object-cover object-center transform hover:scale-102 transition-transform duration-500"
            />
          </div>
        </div>

        {/* Right Side: Big Title and Subtitle */}
        <div className="w-full md:w-1/2 flex flex-col justify-center text-center md:text-left pt-2 sm:pt-6">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-[#1B3B54] tracking-tight font-sans">
            {title}
          </h1>
          <p className="text-slate-600 text-lg sm:text-xl mt-3 sm:mt-4 font-normal tracking-wide">
            {subtitle}
          </p>
        </div>
      </div>
    </section>
  );
};
