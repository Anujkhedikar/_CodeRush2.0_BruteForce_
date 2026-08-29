import { useEffect, useState } from 'react'
import {
  ArrowLeft,
  Clock,
  Coins,
  FileText,
  Loader2,
  MessageSquare,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { marked } from 'marked'

/* ------------------------------------------------------------------ */
/* Types (mirror of the backend /sessions + /sessions/:id contract)    */
/* ------------------------------------------------------------------ */

type SessionMeta = {
  id: string
  preview: string
  updated_at: number
  turn_count: number
  total_tokens: number
}

type HistoryTurn = {
  role: 'user' | 'assistant'
  content: string
  mode?: string
  language?: string
  model?: string
  cost?: number
  duration_ms?: number
}

type Stats = {
  totals: { sessions: number; turns: number; total_tokens: number; cost: number }
  by_mode?: { name: string; tokens: number }[]
  by_day?: { day: string; tokens: number }[]
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || ''

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function relativeTime(t: number): string {
  if (!t) return ''
  const diff = (Date.now() - t * 1000) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return Math.floor(diff / 60) + ' min ago'
  if (diff < 86400) return Math.floor(diff / 3600) + ' hr ago'
  if (diff < 604800) return Math.floor(diff / 86400) + ' days ago'
  return new Date(t * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function fmtInt(v: number | null | undefined): string {
  return v === null || v === undefined ? '0' : Number(v).toLocaleString('en-US')
}

function fmtCost(c: number | null | undefined): string {
  if (c === null || c === undefined) return '$0.00'
  return c >= 0.01 ? '$' + c.toFixed(3) : '$' + c.toFixed(4)
}

const MODE_BADGE: Record<string, string> = {
  explain: 'Explain',
  error_finder: 'Find Errors',
  generate: 'Generate',
  optimize: 'Optimize',
  repo_report: 'Repo Report',
}

/* ------------------------------------------------------------------ */
/* Stat card (compact overview strip)                                  */
/* ------------------------------------------------------------------ */

function StatCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-[#1E2025] bg-[#0E0F12] px-3 py-2.5">
      <span className="text-[#8A91A0]">{icon}</span>
      <div className="min-w-0">
        <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-[#6B7280]">{label}</p>
        <p className="truncate font-mono text-sm text-white">{value}</p>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Session row                                                         */
/* ------------------------------------------------------------------ */

function SessionRow({
  session,
  active,
  onOpen,
  onDelete,
}: {
  session: SessionMeta
  active: boolean
  onOpen: () => void
  onDelete: () => void
}) {
  const [hover, setHover] = useState(false)
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={onOpen}
      className={`group flex cursor-pointer items-center gap-3 rounded-lg border px-3.5 py-3 transition-colors ${
        active
          ? 'border-[#FF6B2B]/40 bg-[#141519]'
          : 'border-[#1E2025] bg-[#0E0F12] hover:border-[#2A2D34] hover:bg-[#121318]'
      }`}
    >
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${
          active ? 'bg-[#FF5B00] text-[#070709]' : 'bg-[#17181C] text-[#FF8A4D]'
        }`}
      >
        <MessageSquare size={14} />
      </span>

      <div className="min-w-0 flex-1">
        <p className={`truncate text-[13px] leading-tight ${active ? 'font-medium text-white' : 'text-[#E6E8EC]'}`}>
          {session.preview || 'Untitled session'}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 font-mono text-[10px] text-[#6B7280]">
          <span className="flex items-center gap-1">
            <Clock size={10} /> {relativeTime(session.updated_at)}
          </span>
          <span className="flex items-center gap-1">
            <MessageSquare size={10} /> {fmtInt(session.turn_count)} turns
          </span>
          {session.total_tokens > 0 && (
            <span className="flex items-center gap-1">
              <Coins size={10} /> {fmtInt(session.total_tokens)} tok
            </span>
          )}
        </div>
      </div>

      {hover && (
        <span className="ml-1 flex shrink-0 items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="rounded-md border border-[#23262C] bg-[#17181C] p-1.5 text-[#8A91A0] transition hover:border-[#FF5B00]/40 hover:text-[#FF5B00]"
            aria-label="Delete session"
            title="Delete session"
          >
            <Trash2 size={13} />
          </button>
        </span>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Transcript bubble                                                   */
/* ------------------------------------------------------------------ */

function Transcript({ turns }: { turns: HistoryTurn[] }) {
  if (turns.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center py-16 text-center">
        <FileText size={28} className="mb-3 text-[#2A2D34]" />
        <p className="text-sm text-[#8A91A0]">Select a session to view its conversation history.</p>
      </div>
    )
  }
  return (
    <div className="space-y-4">
      {turns.map((turn, i) =>
        turn.role === 'user' ? (
          <div key={i} className="flex justify-end">
            <div className="max-w-[82%] rounded-xl rounded-br-sm border border-[#23262C] bg-[#16171B] px-3.5 py-2.5 text-[13px] leading-relaxed text-[#E6E8EC]">
              {turn.content}
            </div>
          </div>
        ) : (
          <div key={i} className="flex justify-start">
            <div className="max-w-[86%]">
              <div className="mb-1.5 flex items-center gap-2">
                <span className="rounded bg-[#FF5B00]/15 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide text-[#FF8A4D]">
                  {turn.mode ? MODE_BADGE[turn.mode] || turn.mode : 'Assistant'}
                </span>
                <span className="font-mono text-[9px] text-[#6B7280]">
                  {turn.model ? turn.model : ''}
                  {turn.cost != null ? ` · ${fmtCost(turn.cost)}` : ''}
                  {turn.duration_ms != null ? ` · ${turn.duration_ms}ms` : ''}
                </span>
              </div>
              <div
                className="mentor-markdown rounded-xl rounded-bl-sm border border-[#1E2025] bg-[#0E0F12] px-4 py-3 text-[13px] leading-relaxed text-[#E6E8EC]"
                dangerouslySetInnerHTML={{
                  __html: marked.parse(turn.content) as string,
                }}
              />
            </div>
          </div>
        ),
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Root page                                                           */
/* ------------------------------------------------------------------ */

export default function RecentSessionsPage() {
  const [sessions, setSessions] = useState<SessionMeta[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [turns, setTurns] = useState<HistoryTurn[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const [sRes, stRes] = await Promise.all([
        fetch(`${API_BASE}/sessions`),
        fetch(`${API_BASE}/stats`),
      ])
      const sData = await sRes.json()
      const stData = await stRes.json()
      setSessions((sData.sessions || []).sort((a: SessionMeta, b: SessionMeta) => b.updated_at - a.updated_at))
      setStats(stData)
    } catch {
      /* noop */
    } finally {
      setLoading(false)
    }
  }

  async function openSession(id: string) {
    setSelectedId(id)
    setBusy(true)
    try {
      const res = await fetch(`${API_BASE}/sessions/${id}`)
      if (!res.ok) {
        setTurns([])
        return
      }
      const data = await res.json()
      setTurns(data.turns || [])
    } catch {
      setTurns([])
    } finally {
      setBusy(false)
    }
  }

  async function deleteSession(id: string) {
    try {
      await fetch(`${API_BASE}/sessions/${id}`, { method: 'DELETE' })
    } catch {
      /* noop */
    }
    if (selectedId === id) {
      setSelectedId(null)
      setTurns([])
    }
    load()
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const totals = stats?.totals

  return (
    <div className="mentor-scroll min-h-0 flex-1 overflow-y-auto px-4 py-5 lg:px-6">
      <div className="mx-auto max-w-6xl">
        {/* Stats strip */}
        <div className="mb-5 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          <StatCard label="Sessions" value={fmtInt(totals?.sessions)} icon={<Sparkles size={15} />} />
          <StatCard label="Turns" value={fmtInt(totals?.turns)} icon={<MessageSquare size={15} />} />
          <StatCard label="Tokens" value={fmtInt(totals?.total_tokens)} icon={<Coins size={15} />} />
          <StatCard label="Cost" value={fmtCost(totals?.cost)} icon={<Coins size={15} />} />
        </div>

          <div className="grid gap-5 lg:grid-cols-[1fr_1.1fr]">
            {/* Sessions list */}
            <div className="min-w-0">
              <h2 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B7280]">
                Conversation History
              </h2>
              {loading ? (
                <div className="space-y-2.5">
                  {[0, 1, 2, 3].map((i) => (
                    <div key={i} className="h-[64px] animate-pulse rounded-lg bg-[#121318]" />
                  ))}
                </div>
              ) : sessions.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-[#2A2D34] py-16 text-center">
                  <MessageSquare size={28} className="mb-3 text-[#2A2D34]" />
                  <p className="text-sm text-[#8A91A0]">No sessions yet. Start a conversation in the playground.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {sessions.map((s) => (
                    <SessionRow
                      key={s.id}
                      session={s}
                      active={s.id === selectedId}
                      onOpen={() => openSession(s.id)}
                      onDelete={() => deleteSession(s.id)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Transcript detail */}
            <div className="min-w-0">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B7280]">
                  {selectedId ? 'Session Detail' : 'Detail'}
                </h2>
                {selectedId && (
                  <button
                    onClick={() => {
                      setSelectedId(null)
                      setTurns([])
                    }}
                    className="flex items-center gap-1.5 rounded-md border border-[#23262C] bg-[#141519] px-2.5 py-1 text-[11px] text-[#8A91A0] transition hover:border-[#FF6B2B]/40 hover:text-white"
                  >
                    <ArrowLeft size={12} /> Back
                  </button>
                )}
              </div>
              <div className="mentor-scroll max-h-[70vh] overflow-y-auto rounded-lg border border-[#1E2025] bg-[#0A0B0E] p-4">
                {busy ? (
                  <div className="flex items-center justify-center gap-2 py-12 text-[#6B7280]">
                    <Loader2 size={16} className="animate-spin" /> Loading…
                  </div>
                ) : (
                  <Transcript turns={turns} />
                )}
              </div>
</div>
        </div>
      </div>
    </div>
  )
}
