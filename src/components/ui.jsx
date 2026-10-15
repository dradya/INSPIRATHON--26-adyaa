import { motion } from 'framer-motion'
export function GlassCard({ children, className = '', delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className={`glass rounded-2xl p-5 shadow-card ${className}`}
    >
      {children}
    </motion.div>
  )
}
export function Stat({ label, value, sub }) {
  return (
    <div className="glass-soft rounded-2xl p-4">
      <div className="font-display text-3xl font-bold">{value}</div>
      <div className="mt-1 text-xs font-semibold uppercase tracking-widest text-white/50">{label}</div>
      {sub && <div className="mt-1 text-xs text-white/50">{sub}</div>}
    </div>
  )
}
export function Empty({ title, hint }) {
  return (
    <div className="glass-soft rounded-2xl p-10 text-center">
      <div className="font-display text-lg font-bold">{title}</div>
      <div className="mt-1 text-sm text-white/50">{hint}</div>
    </div>
  )
}
