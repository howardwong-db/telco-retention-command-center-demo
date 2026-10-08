import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Send,
  Plus,
  Trash2,
  MessageSquare,
  Bot,
  Sparkles,
  Loader2,
  Network,
} from 'lucide-react'
import { getJSON, postJSON, del } from '../api'
import { Header } from './Dashboard'

interface Msg { role: 'user' | 'assistant'; content: string }
interface Conv { id: string; title: string; updated_at?: string }

const SUGGESTED = [
  'What retention offer works best against T-Mobile Home Internet?',
  'Which agents need coaching?',
  "What's our churn rate vs baseline?",
]

const ROUTING_STEPS = [
  'Routing your question to the supervisor…',
  'Consulting the Genie analyst on live call data…',
  'Checking the retention knowledge base…',
  'Synthesizing a recommendation…',
]

export default function Assistant() {
  const [convs, setConvs] = useState<Conv[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [persistence, setPersistence] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => { loadConvs() }, [])
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  async function loadConvs() {
    try {
      const d = await getJSON<{ conversations: Conv[]; persistence: boolean }>('/api/conversations')
      setConvs(d.conversations)
      setPersistence(d.persistence)
    } catch { setPersistence(false) }
  }

  async function openConv(id: string) {
    setActiveId(id)
    try {
      const d = await getJSON<{ messages: Msg[] }>(`/api/conversations/${id}/messages`)
      setMessages(d.messages)
    } catch { setMessages([]) }
  }

  function newChat() {
    setActiveId(null)
    setMessages([])
    setInput('')
  }

  async function deleteConv(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    await del(`/api/conversations/${id}`).catch(() => {})
    if (activeId === id) newChat()
    loadConvs()
  }

  async function ensureConv(firstMsg: string): Promise<string | null> {
    if (activeId) return activeId
    if (!persistence) { const tmp = `local-${Date.now()}`; setActiveId(tmp); return tmp }
    try {
      const c = await postJSON<{ id: string; title: string }>('/api/conversations', {
        title: firstMsg.slice(0, 60),
      })
      setActiveId(c.id)
      loadConvs()
      return c.id
    } catch { const tmp = `local-${Date.now()}`; setActiveId(tmp); return tmp }
  }

  async function persist(convId: string, role: string, content: string) {
    if (!persistence || convId.startsWith('local-')) return
    await postJSON(`/api/conversations/${convId}/messages`, { role, content }).catch(() => {})
  }

  async function send(text: string) {
    const msg = text.trim()
    if (!msg || busy) return
    setInput('')
    const history = messages.slice(-8)
    const convId = await ensureConv(msg)
    const userMsg: Msg = { role: 'user', content: msg }
    setMessages((m) => [...m, userMsg])
    if (convId) persist(convId, 'user', msg)

    setBusy(true)
    setElapsed(0)
    const timer = setInterval(() => setElapsed((e) => +(e + 0.1).toFixed(1)), 100)
    try {
      const { job_id } = await postJSON<{ job_id: string }>('/api/chat', {
        message: msg,
        history,
      })
      // Poll
      let done = false
      while (!done) {
        await new Promise((r) => setTimeout(r, 1500))
        const s = await getJSON<{ status: string; response?: string; error?: string }>(
          `/api/chat/${job_id}`,
        )
        if (s.status === 'done') {
          done = true
          const a: Msg = { role: 'assistant', content: s.response || '' }
          setMessages((m) => [...m, a])
          if (convId) persist(convId, 'assistant', a.content)
        } else if (s.status === 'error') {
          done = true
          setMessages((m) => [
            ...m,
            { role: 'assistant', content: `⚠️ The assistant hit an error: ${s.error}. Please try again.` },
          ])
        }
      }
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠️ Request failed: ${String(e)}` }])
    } finally {
      clearInterval(timer)
      setBusy(false)
    }
  }

  const routingStep = ROUTING_STEPS[Math.min(ROUTING_STEPS.length - 1, Math.floor(elapsed / 6))]

  return (
    <div className="space-y-6 h-full flex flex-col">
      <Header title="AI Assistant" subtitle="Multi-agent retention intelligence — routes across live call data and the retention playbook" />

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-5 flex-1 min-h-0">
        {/* Conversation list */}
        <div className="card p-3 flex flex-col min-h-0">
          <button onClick={newChat}
            className="flex items-center justify-center gap-2 rounded-lg bg-spectrum-blue/90 hover:bg-spectrum-blue text-white text-sm font-semibold py-2.5 transition-colors">
            <Plus size={16} /> New chat
          </button>
          <div className="mt-3 flex-1 overflow-y-auto space-y-1">
            {convs.length === 0 && (
              <div className="text-xs text-slate-500 px-2 py-4 text-center">
                {persistence ? 'No conversations yet' : 'Persistence unavailable locally'}
              </div>
            )}
            {convs.map((c) => (
              <div key={c.id} onClick={() => openConv(c.id)}
                className={`group flex items-center gap-2 rounded-lg px-2.5 py-2 cursor-pointer text-sm transition-colors ${
                  activeId === c.id ? 'bg-spectrum-blue/15 text-white' : 'text-slate-400 hover:bg-white/5'
                }`}>
                <MessageSquare size={14} className="shrink-0" />
                <span className="truncate flex-1">{c.title}</span>
                <button onClick={(e) => deleteConv(c.id, e)}
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-accent-red transition-opacity">
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Chat area */}
        <div className="card p-0 flex flex-col min-h-0 overflow-hidden">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-5">
            {messages.length === 0 && !busy && <EmptyState onPick={send} />}
            {messages.map((m, i) => <Bubble key={i} msg={m} />)}
            {busy && <RoutingBubble elapsed={elapsed} step={routingStep} />}
          </div>

          {/* Composer */}
          <div className="border-t border-white/5 p-4">
            {messages.length > 0 && !busy && (
              <div className="flex flex-wrap gap-2 mb-3">
                {SUGGESTED.map((s) => (
                  <button key={s} onClick={() => send(s)}
                    className="text-xs rounded-full border border-white/10 px-3 py-1.5 text-slate-300 hover:border-spectrum-sky/40 hover:text-white transition-colors">
                    {s}
                  </button>
                ))}
              </div>
            )}
            <div className="flex items-end gap-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input) }
                }}
                rows={1}
                placeholder="Ask about churn, offers, competitors, or agent performance…"
                className="flex-1 resize-none rounded-xl bg-navy-900/70 border border-white/10 focus:border-spectrum-sky/50 outline-none px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 max-h-40"
              />
              <button onClick={() => send(input)} disabled={busy || !input.trim()}
                className="h-11 w-11 shrink-0 rounded-xl bg-spectrum-blue hover:bg-spectrum-sky disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-white transition-colors">
                {busy ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function EmptyState({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center py-8">
      <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-spectrum-blue to-spectrum-sky flex items-center justify-center shadow-glow mb-4">
        <Bot size={28} className="text-navy-950" />
      </div>
      <h3 className="text-lg font-bold text-white">Retention Intelligence Assistant</h3>
      <p className="text-sm text-slate-400 max-w-md mt-1">
        Ask a question and the multi-agent supervisor routes it to live call analytics and the retention playbook.
      </p>
      <div className="grid sm:grid-cols-1 gap-2.5 mt-6 w-full max-w-lg">
        {SUGGESTED.map((s) => (
          <button key={s} onClick={() => onPick(s)}
            className="flex items-center gap-3 text-left rounded-xl border border-white/10 bg-navy-900/50 px-4 py-3 text-sm text-slate-200 hover:border-spectrum-sky/40 hover:bg-navy-800 transition-colors">
            <Sparkles size={16} className="text-spectrum-sky shrink-0" />
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

function Bubble({ msg }: { msg: Msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="h-8 w-8 shrink-0 rounded-lg bg-gradient-to-br from-spectrum-blue to-spectrum-sky flex items-center justify-center">
          <Bot size={16} className="text-navy-950" />
        </div>
      )}
      <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm ${
        isUser ? 'bg-spectrum-blue text-white rounded-br-sm' : 'bg-navy-900/80 border border-white/5 text-slate-100 rounded-bl-sm'
      }`}>
        {isUser ? <span className="whitespace-pre-wrap">{msg.content}</span> : (
          <div className="md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

function RoutingBubble({ elapsed, step }: { elapsed: number; step: string }) {
  return (
    <div className="flex gap-3 justify-start">
      <div className="h-8 w-8 shrink-0 rounded-lg bg-gradient-to-br from-spectrum-blue to-spectrum-sky flex items-center justify-center">
        <Network size={16} className="text-navy-950 animate-pulse" />
      </div>
      <div className="rounded-2xl rounded-bl-sm bg-navy-900/80 border border-white/5 px-4 py-3 min-w-[280px]">
        <div className="flex items-center gap-2 text-sm text-slate-200">
          <Loader2 size={14} className="animate-spin text-spectrum-sky" />
          <span>{step}</span>
        </div>
        <div className="mt-2.5 flex items-center gap-2">
          <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-spectrum-blue to-spectrum-sky animate-pulse"
              style={{ width: `${Math.min(95, elapsed * 4)}%` }} />
          </div>
          <span className="text-xs tabular-nums text-slate-400 w-12 text-right">{elapsed.toFixed(1)}s</span>
        </div>
      </div>
    </div>
  )
}
