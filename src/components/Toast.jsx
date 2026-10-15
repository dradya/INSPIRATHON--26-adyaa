import { createContext, useCallback, useContext, useState } from 'react'
import { CheckCircle2, AlertTriangle, Info } from 'lucide-react'

const ToastCtx = createContext(null)
export const useToast = () => useContext(ToastCtx)
let idSeq = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const push = useCallback((msg, kind = 'ok') => {
    const id = ++idSeq
    setToasts((t) => [...t.slice(-3), { id, msg, kind }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3200)
  }, [])

  const toast = useCallback((msg) => push(msg, 'ok'), [push])
  toast.ok = (m) => push(m, 'ok')
  toast.err = (m) => push(m, 'err')
  toast.info = (m) => push(m, 'info')

  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div className="fixed bottom-5 left-5 z-[90] flex w-[320px] flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} className="glass flex items-center gap-2.5 rounded-xl px-4 py-3 text-sm shadow-card">
            {t.kind === 'ok' && <CheckCircle2 size={16} className="shrink-0 text-mint" />}
            {t.kind === 'err' && <AlertTriangle size={16} className="shrink-0 text-red-300" />}
            {t.kind === 'info' && <Info size={16} className="shrink-0 text-neon" />}
            <span className="text-white/85">{t.msg}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}
