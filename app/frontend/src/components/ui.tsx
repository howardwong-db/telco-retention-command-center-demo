import React from 'react'

export function Card({
  title,
  right,
  className = '',
  children,
}: {
  title?: string
  right?: React.ReactNode
  className?: string
  children: React.ReactNode
}) {
  return (
    <div className={`card p-5 ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between mb-4">
          {title && <h3 className="card-hd">{title}</h3>}
          {right}
        </div>
      )}
      {children}
    </div>
  )
}

export function Kpi({
  label,
  value,
  sub,
  icon,
  tone = 'blue',
}: {
  label: string
  value: string
  sub?: React.ReactNode
  icon?: React.ReactNode
  tone?: 'blue' | 'red' | 'amber' | 'green'
}) {
  const tones: Record<string, string> = {
    blue: 'from-spectrum-blue/20 to-transparent text-spectrum-sky',
    red: 'from-accent-red/20 to-transparent text-accent-red',
    amber: 'from-accent-amber/20 to-transparent text-accent-amber',
    green: 'from-accent-green/20 to-transparent text-accent-green',
  }
  return (
    <div className="card p-5 relative overflow-hidden">
      <div className={`absolute inset-0 bg-gradient-to-br ${tones[tone]} opacity-60 pointer-events-none`} />
      <div className="relative">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
            {label}
          </span>
          <span className={tones[tone].split(' ').pop()}>{icon}</span>
        </div>
        <div className="mt-3 text-3xl font-extrabold text-white tabular-nums">{value}</div>
        {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
      </div>
    </div>
  )
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-slate-400 gap-3">
      <div className="h-5 w-5 rounded-full border-2 border-spectrum-sky/40 border-t-spectrum-sky animate-spin" />
      {label}
    </div>
  )
}

export function ErrorBox({ msg }: { msg: string }) {
  return (
    <div className="card p-5 border-accent-red/40 text-accent-red text-sm">
      Failed to load: {msg}
    </div>
  )
}

export function Pill({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold"
      style={{ background: `${color}22`, color }}
    >
      {children}
    </span>
  )
}
