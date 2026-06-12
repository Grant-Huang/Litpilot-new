'use client';

import { useState, useCallback, createContext, useContext } from 'react';

interface Toast {
  id: number;
  message: string;
  type: 'info' | 'success' | 'error';
}

interface ToastCtx {
  addToast: (message: string, type?: Toast['type']) => void;
}

const ToastContext = createContext<ToastCtx>({ addToast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  let _id = 0;

  const addToast = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = Date.now() + (_id++);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`
              px-4 py-2 rounded-[var(--lp-radius-md)] shadow-lg text-sm font-medium
              animate-[slideIn_0.2s_ease-out]
              ${t.type === 'error' ? 'bg-red-600 text-white' :
                t.type === 'success' ? 'bg-green-600 text-white' :
                'bg-[var(--lp-ink)] text-white'}
            `}
          >
            {t.message}
          </div>
        ))}
      </div>
      <style jsx>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </ToastContext.Provider>
  );
}
