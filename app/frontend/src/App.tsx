import { useEffect, useState } from 'react'
import {
  LayoutDashboard,
  Bot,
  Swords,
  GraduationCap,
  Radio,
  User,
} from 'lucide-react'
import { getJSON } from './api'
import Dashboard from './tabs/Dashboard'
import Assistant from './tabs/Assistant'
import Competitors from './tabs/Competitors'
import Coaching from './tabs/Coaching'

type TabId = 'dashboard' | 'assistant' | 'competitors' | 'coaching'

const TABS: { id: TabId; label: string; icon: React.ReactNode; desc: string }[] = [
  { id: 'dashboard', label: 'Executive Dashboard', icon: <LayoutDashboard size={18} />, desc: 'Churn & retention KPIs' },
  { id: 'assistant', label: 'AI Assistant', icon: <Bot size={18} />, desc: 'Ask the retention agent' },
  { id: 'competitors', label: 'Competitor Intelligence', icon: <Swords size={18} />, desc: 'Counter-offers & talk tracks' },
  { id: 'coaching', label: 'Agent Coaching', icon: <GraduationCap size={18} />, desc: 'Performance & coaching' },
]

export default function App() {
  const [tab, setTab] = useState<TabId>('dashboard')
  const [email, setEmail] = useState<string>('')

  useEffect(() => {
    getJSON<{ email: string }>('/api/me')
      .then((d) => setEmail(d.email))
      .catch(() => setEmail('unknown user'))
  }, [])

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-72 shrink-0 flex flex-col border-r border-white/5 bg-navy-950/70 backdrop-blur">
        <div className="px-6 pt-6 pb-5 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-spectrum-blue to-spectrum-sky flex items-center justify-center shadow-glow">
              <Radio size={20} className="text-navy-950" />
            </div>
            <div>
              <div className="text-white font-extrabold leading-tight tracking-tight">TelcoABC</div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-spectrum-sky font-semibold">
                Retention Center
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {TABS.map((t) => {
            const active = tab === t.id
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`w-full flex items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-all ${
                  active
                    ? 'bg-spectrum-blue/15 text-white shadow-[inset_0_0_0_1px_rgba(52,195,240,0.3)]'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                <span className={active ? 'text-spectrum-sky mt-0.5' : 'mt-0.5'}>{t.icon}</span>
                <span>
                  <span className="block text-sm font-semibold leading-tight">{t.label}</span>
                  <span className="block text-[11px] text-slate-500 leading-tight mt-0.5">{t.desc}</span>
                </span>
              </button>
            )
          })}
        </nav>

        {/* User identity bottom-left */}
        <div className="px-4 py-4 border-t border-white/5">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-navy-700 flex items-center justify-center text-spectrum-sky">
              <User size={16} />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] text-slate-500 uppercase tracking-wider">Signed in</div>
              <div className="text-xs text-slate-200 truncate" title={email}>
                {email || '…'}
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1500px] mx-auto px-8 py-7">
          {tab === 'dashboard' && <Dashboard />}
          {tab === 'assistant' && <Assistant />}
          {tab === 'competitors' && <Competitors />}
          {tab === 'coaching' && <Coaching />}
        </div>
      </main>
    </div>
  )
}
