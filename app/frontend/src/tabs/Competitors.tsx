import { useEffect, useState } from 'react'
import {
  ChevronDown,
  AlertTriangle,
  Tag,
  Megaphone,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react'
import { getJSON, pct, COMPETITOR_COLORS } from '../api'
import { Loading, ErrorBox, Pill } from '../components/ui'
import { Header } from './Dashboard'

interface Offer { offer_id: string; offer_name: string; save_rate: number; monthly_cost: number }
interface Competitor {
  name: string; market_share: number; positioning: string; pricing: string
  weaknesses: string[]; best_counter: string; counter_offer_id: string
  talk_track: string; counter_offer: Offer | null
}

export default function Competitors() {
  const [data, setData] = useState<Competitor[] | null>(null)
  const [err, setErr] = useState('')
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    getJSON<{ competitors: Competitor[] }>('/api/competitors')
      .then((d) => { setData(d.competitors); setOpen(d.competitors[0]?.name ?? null) })
      .catch((e) => setErr(String(e)))
  }, [])

  if (err) return <ErrorBox msg={err} />
  if (!data) return <Loading label="Loading competitor intelligence…" />

  return (
    <div className="space-y-6">
      <Header title="Competitor Intelligence" subtitle="Market share, weaknesses, best counter-offers, and ready-to-use talk tracks" />

      <div className="space-y-3">
        {data.map((c, i) => {
          const color = COMPETITOR_COLORS[i % COMPETITOR_COLORS.length]
          const isOpen = open === c.name
          return (
            <div key={c.name} className="card overflow-hidden">
              <button onClick={() => setOpen(isOpen ? null : c.name)}
                className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-white/5 transition-colors">
                <div className="h-10 w-1.5 rounded-full" style={{ background: color }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className="text-base font-bold text-white">{c.name}</span>
                    <Pill color={color}>{c.market_share}% share</Pill>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5 truncate">{c.positioning}</div>
                </div>
                {/* share bar */}
                <div className="hidden md:block w-40">
                  <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${c.market_share * 2.4}%`, background: color }} />
                  </div>
                </div>
                {c.counter_offer && (
                  <div className="hidden lg:flex flex-col items-end mr-2">
                    <span className="text-xs text-slate-500">Best counter save rate</span>
                    <span className="text-sm font-bold text-accent-green tabular-nums">
                      {pct(c.counter_offer.save_rate)}
                    </span>
                  </div>
                )}
                <ChevronDown size={20} className={`text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
              </button>

              {isOpen && (
                <div className="px-5 pb-5 pt-1 grid grid-cols-1 lg:grid-cols-3 gap-5 border-t border-white/5">
                  {/* Pricing */}
                  <Section icon={<Tag size={15} />} title="Pricing" color={color}>
                    <p className="text-sm text-slate-300 leading-relaxed">{c.pricing}</p>
                  </Section>

                  {/* Weaknesses */}
                  <Section icon={<AlertTriangle size={15} />} title="Weaknesses to Exploit" color="#f5a623">
                    <ul className="space-y-1.5">
                      {c.weaknesses.map((w, j) => (
                        <li key={j} className="text-sm text-slate-300 flex gap-2 leading-snug">
                          <span className="text-accent-amber mt-0.5">▸</span>{w}
                        </li>
                      ))}
                    </ul>
                  </Section>

                  {/* Best counter */}
                  <Section icon={<ShieldCheck size={15} />} title="Recommended Counter-Offer" color="#2dce89">
                    <div className="rounded-lg bg-accent-green/10 border border-accent-green/20 p-3">
                      <div className="text-sm font-bold text-white">{c.best_counter}</div>
                      {c.counter_offer && (
                        <div className="flex items-center gap-4 mt-2 text-xs text-slate-300">
                          <span className="flex items-center gap-1 text-accent-green font-semibold">
                            <TrendingUp size={13} /> {pct(c.counter_offer.save_rate)} save rate
                          </span>
                          <span>${c.counter_offer.monthly_cost.toFixed(0)}/mo cost</span>
                          <Pill color="#0099d8">{c.counter_offer.offer_id}</Pill>
                        </div>
                      )}
                    </div>
                  </Section>

                  {/* Talk track full width */}
                  <div className="lg:col-span-3">
                    <Section icon={<Megaphone size={15} />} title="Ready-to-Use Talk Track" color="#34c3f0">
                      <div className="rounded-lg bg-navy-900/70 border-l-2 border-spectrum-sky p-4 text-sm text-slate-200 italic leading-relaxed">
                        {c.talk_track}
                      </div>
                    </Section>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Section({ icon, title, color, children }: { icon: React.ReactNode; title: string; color: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2 text-xs font-semibold uppercase tracking-wider" style={{ color }}>
        {icon} {title}
      </div>
      {children}
    </div>
  )
}
