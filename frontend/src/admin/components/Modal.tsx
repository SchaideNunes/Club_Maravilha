import React, { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

export type ModalProps = {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  titleId?: string;
  ariaLabel?: string;
  maxWidth?: string;
  children: React.ReactNode;
};

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Modal({
  isOpen,
  onClose,
  title,
  titleId,
  ariaLabel,
  maxWidth = 'max-w-md',
  children,
}: ModalProps): React.ReactElement | null {
  const generatedId = useId();
  const computedTitleId = titleId || `modal-title-${generatedId}`;
  const containerRef = useRef<HTMLDivElement>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  // Armazena elemento focado anteriormente e restaura ao desmontar / fechar
  useEffect(() => {
    const previousElement = (document.activeElement as HTMLElement | null) || previousActiveElementRef.current;
    previousActiveElementRef.current = previousElement;
    return () => {
      if (previousElement && typeof previousElement.focus === 'function') {
        try {
          previousElement.focus();
        } catch {
          // Ignora se o elemento não existir mais no DOM
        }
      }
    };
  }, []);

  // Foco inicial no primeiro campo editável e tratamento de teclas (Escape e Focus Trap)
  useEffect(() => {
    if (!isOpen) return;

    // Foco inicial: prioriza campos editáveis (input, select, textarea), ou o primeiro focável
    const focusTimeout = window.setTimeout(() => {
      if (!containerRef.current) return;
      const inputs = containerRef.current.querySelectorAll<HTMLElement>(
        'input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled])'
      );
      if (inputs.length > 0) {
        inputs[0].focus();
        return;
      }
      const allFocusable = containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (allFocusable.length > 0) {
        allFocusable[0].focus();
      }
    }, 10);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }

      if (e.key === 'Tab') {
        if (!containerRef.current) return;
        const focusable = Array.from(
          containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
        ).filter((el) => el.offsetParent !== null || el.getAttribute('type') !== 'hidden');

        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.clearTimeout(focusTimeout);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={computedTitleId}
      aria-label={ariaLabel || title}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
    >
      <div
        ref={containerRef}
        className={`bg-white rounded-xl shadow-xl border border-slate-200 w-full ${maxWidth} p-6 relative`}
      >
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <h2 id={computedTitleId} className="text-lg font-semibold text-slate-900">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="text-slate-400 hover:text-slate-600 rounded-lg p-1 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}

export default Modal;
