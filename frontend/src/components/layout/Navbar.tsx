import { useState, useEffect } from 'react';
import { 
  Menu, 
  X, 
  Phone, 
  Mail, 
  User, 
  ChevronRight
} from 'lucide-react';

interface NavbarProps {
  onOpenPortal: () => void;
  onNavigateSection: (sectionId: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenPortal, onNavigateSection }) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 30);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: 'Início', target: 'hero' },
    { label: 'Estrutura & Lazer', target: 'facilities' },
    { label: 'Quadras Esportivas', target: 'courts' },
    { label: 'Tecnologia & Catraca', target: 'technology' },
    { label: 'Contato', target: 'contact' },
  ];

  const handleLinkClick = (target: string) => {
    onNavigateSection(target);
    setMobileMenuOpen(false);
  };

  return (
    <>
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled
            ? 'bg-slate-950/75 backdrop-blur-lg border-b border-white/10 shadow-2xl shadow-black/40'
            : 'bg-slate-950/30 backdrop-blur-md border-b border-white/10'
        }`}
      >
        {/* Top Info Bar (Estilo Resort Amoja: telefone, email, horário) */}
        <div className="hidden lg:block border-b border-white/5 text-[12px] text-slate-300/90 font-light">
          <div className="max-w-7xl mx-auto px-6 h-9 flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <a 
                href="https://wa.me/5511999998888" 
                target="_blank" 
                rel="noreferrer"
                className="flex items-center space-x-1.5 hover:text-amber-300 transition-colors"
              >
                <Phone className="w-3 h-3 text-amber-400" />
                <span>+55 (11) 99999-8888</span>
              </a>
              <span className="text-white/20">•</span>
              <a 
                href="mailto:secretaria@clubmaravilha.com.br"
                className="flex items-center space-x-1.5 hover:text-amber-300 transition-colors"
              >
                <Mail className="w-3 h-3 text-amber-400" />
                <span>secretaria@clubmaravilha.com.br</span>
              </a>
            </div>

            <div className="flex items-center space-x-5">
              <div className="flex items-center space-x-1.5 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Aberto hoje até 22h00</span>
              </div>
              <span className="text-white/20">•</span>
              <span className="text-slate-400">Exclusivo para ~300 Associados</span>
            </div>
          </div>
        </div>

        {/* Main Navbar */}
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          {/* Logo Estilo Resort de Luxo */}
          <button 
            onClick={() => handleLinkClick('hero')}
            className="flex items-center space-x-3 group text-left focus:outline-none"
          >
            <div className="w-10 h-10 rounded-full border border-amber-400/40 bg-gradient-to-tr from-slate-900 to-amber-950/40 flex items-center justify-center text-amber-400 group-hover:border-amber-300 transition-all duration-300 shadow-lg shadow-black/30">
              <span className="font-serif text-lg tracking-wider font-semibold">CM</span>
            </div>
            <div className="flex flex-col">
              <span className="font-serif tracking-widest2 text-lg sm:text-xl font-medium text-white group-hover:text-amber-200 transition-colors uppercase">
                Club Maravilha
              </span>
              <span className="text-[9px] uppercase tracking-widest text-amber-300/80 font-sans font-light">
                Esporte & Convivência
              </span>
            </div>
          </button>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex items-center space-x-8">
            {navLinks.map((link) => (
              <button
                key={link.target}
                onClick={() => handleLinkClick(link.target)}
                className="text-xs uppercase tracking-wider text-slate-200/90 hover:text-amber-300 transition-all duration-200 font-medium relative group py-1"
              >
                {link.label}
                <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-amber-400 group-hover:w-full transition-all duration-300"></span>
              </button>
            ))}
          </nav>

          {/* Desktop Action Buttons */}
          <div className="hidden lg:flex items-center space-x-4">
            <button
              onClick={onOpenPortal}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-amber-500/90 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-semibold text-xs tracking-wider uppercase shadow-lg shadow-amber-900/30 hover:shadow-amber-500/20 transition-all duration-300 transform hover:-translate-y-0.5"
            >
              <User className="w-3.5 h-3.5" />
              <span>Área do Associado</span>
            </button>
          </div>

          {/* Mobile Hamburger Button (Lateral Direita) */}
          <div className="lg:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Abrir Menu de Navegação"
              className="p-2 rounded-xl bg-white/5 border border-white/10 text-slate-100 hover:text-amber-300 hover:bg-white/10 transition-colors focus:outline-none"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer Backdrop */}
      {mobileMenuOpen && (
        <div 
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 transition-opacity duration-300 lg:hidden"
        />
      )}

      {/* Mobile Drawer - Preenchendo 30% da tela na lateral direita conforme instrução */}
      <aside
        className={`fixed top-0 right-0 bottom-0 z-50 bg-slate-950/95 backdrop-blur-2xl border-l border-white/10 shadow-2xl transition-transform duration-300 ease-out flex flex-col justify-between lg:hidden ${
          mobileMenuOpen ? 'translate-x-0' : 'translate-x-full'
        } w-[30%] min-w-[270px] sm:min-w-[300px]`}
      >
        <div>
          {/* Drawer Header */}
          <div className="p-6 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-full border border-amber-400/40 bg-amber-950/40 flex items-center justify-center text-amber-400 font-serif text-sm font-semibold">
                CM
              </div>
              <span className="font-serif tracking-wider text-sm font-semibold text-white">
                Club Maravilha
              </span>
            </div>
            <button
              onClick={() => setMobileMenuOpen(false)}
              aria-label="Fechar Menu"
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-6 space-y-4">
            {navLinks.map((link) => (
              <button
                key={link.target}
                onClick={() => handleLinkClick(link.target)}
                className="w-full text-left py-2 text-xs uppercase tracking-wider text-slate-300 hover:text-amber-400 transition-colors flex items-center justify-between border-b border-white/5"
              >
                <span>{link.label}</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
              </button>
            ))}
          </nav>
        </div>

        {/* Drawer Footer & Actions */}
        <div className="p-6 border-t border-white/10 space-y-4 bg-slate-900/40">
          <button
            onClick={() => {
              setMobileMenuOpen(false);
              onOpenPortal();
            }}
            className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider flex items-center justify-center space-x-2 shadow-lg shadow-amber-900/30 transition-all"
          >
            <User className="w-4 h-4" />
            <span>Portal do Sócio</span>
          </button>

          <div className="text-[11px] text-slate-400 space-y-1.5 pt-2">
            <div className="flex items-center space-x-1.5 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>Aberto hoje até 22h</span>
            </div>
            <p>Tel: (11) 99999-8888</p>
            <p className="text-[10px] text-slate-500">Exclusivo para associados</p>
          </div>
        </div>
      </aside>
    </>
  );
};
