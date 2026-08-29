import { useEffect, useRef, useState } from 'react'
import {
  Bot,
  Braces,
  Bug,
  ChevronDown,
  Coins,
  Code,
  GitBranch,
  Send,
  Sparkles,
  Terminal,
  Zap,
} from 'lucide-react'
import { marked } from 'marked'
import PlaygroundSidebar from './PlaygroundSidebar'
import RecentSessionsPage from './RecentSessionsPage'
import CursorGlow from './CursorGlow'

/* ------------------------------------------------------------------ */
/* Types (mirror of the backend /mentor + /sessions + /stats contract) */
/* ------------------------------------------------------------------ */

type MentorMode = 'explain' | 'error_finder' | 'generate' | 'optimize' | 'repo_report'

type ChatTurn = {
  role: 'user' | 'assistant'
  content: string
  mode?: string
  language?: string
  timestamp?: number
  input_check?: { issues?: unknown[] }
  model?: string
  cost?: number
  duration_ms?: number
  context?: { trimmed_turns?: number; memory_turns?: number }
}

export type Stats = {
  totals: { sessions: number; turns: number; total_tokens: number; cost: number }
  by_mode?: { name: string; tokens: number }[]
  by_day?: { day: string; tokens: number }[]
}

type LanguageOption = { value: string; label: string }
type ModelOption = { value: string; label: string }

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || ''

const MODE_META: Record<
  MentorMode,
  { label: string; desc: string; icon: typeof Code; thinking: string; sub: string }
> = {
  explain: {
    label: 'Explain',
    desc: 'Step-by-step logic breakdown',
    icon: Code,
    thinking: 'Analyzing code',
    sub: 'Preparing line-by-line explanation',
  },
  error_finder: {
    label: 'Find Errors',
    desc: 'Detect syntax & logic flaws',
    icon: Bug,
    thinking: 'Scanning for issues',
    sub: 'Checking syntax and logic',
  },
  generate: {
    label: 'Generate',
    desc: 'Build clean implementation',
    icon: Sparkles,
    thinking: 'Generating solution',
    sub: 'Writing clean, commented code',
  },
  optimize: {
    label: 'Optimize',
    desc: 'Improve clarity & performance',
    icon: Zap,
    thinking: 'Optimizing implementation',
    sub: 'Improving clarity and performance',
  },
  repo_report: {
    label: 'Repo Report',
    desc: 'Analyze repository architecture',
    icon: GitBranch,
    thinking: 'Scanning repository',
    sub: 'Mapping structure and detecting errors',
  },
}

const LANGUAGES: LanguageOption[] = [
  { value: 'python', label: 'Python' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
  { value: 'cpp', label: 'C++' },
  { value: 'c', label: 'C' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
  { value: 'javascript', label: 'JavaScript' },
]

const MODELS: ModelOption[] = [
  { value: 'default', label: 'Default model' },
  { value: 'fast', label: 'Fast / low-latency' },
  { value: 'deep', label: 'Deep / high quality' },
]

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const fmtInt = (v: number | null | undefined): string =>
  v === null || v === undefined ? '?' : Number(v).toLocaleString('en-US')

const fmtCost = (c: number | null | undefined): string => {
  if (c === null || c === undefined) return '?'
  return c >= 0.01 ? '$' + Number(c).toFixed(3) : '$' + Number(c).toFixed(4)
}

/* ------------------------------------------------------------------ */
/* Small presentational primitives                                     */
/* ------------------------------------------------------------------ */

function PulseDot({ color }: { color: string }) {
  return (
    <span className="relative flex h-2 w-2">
      <span
        className="absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping"
        style={{ backgroundColor: color }}
      />
      <span className="relative inline-flex h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
    </span>
  )
}

/* ================================================================== */
/* Top Navigation Bar                                                  */
/* ================================================================== */

function TopNav({ online }: { online: boolean }) {
  return (
    <header className="sticky top-0 z-40 h-14 shrink-0 border-b border-[#1A1C22] bg-[#0A0B0E]/90 backdrop-blur">
      <div className="flex h-full items-center gap-3 px-3 lg:px-5">
        <div className="flex items-center gap-2.5">
          <svg className="h-7 w-7 shrink-0" viewBox="0 0 100 100" fill="none" aria-hidden="true">
            <path d="M54 41L84 16L72 31L54 41Z" fill="url(#yukti-orange)" />
            <path d="M20 29L36 29L51 46L42 76L42 46L20 29Z" fill="#FFFFFF" />
            <path d="M51 46L75 34L42 76L51 46Z" fill="url(#yukti-orange)" />
            <defs>
              <linearGradient id="yukti-orange" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FF8A4D" />
                <stop offset="100%" stopColor="#FF5B00" />
              </linearGradient>
            </defs>
          </svg>
          <span className="hidden whitespace-nowrap text-[14px] font-extrabold tracking-tight text-white sm:inline">
            YUKTI
          </span>
        </div>

        <div className="ml-auto flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 rounded-full border border-[#1f3d2e] bg-[#0c1410] px-2.5 py-1">
            <PulseDot color={online ? '#00E599' : '#FF5B00'} />
            <span className="hidden text-xs font-medium text-[#10B981] sm:inline">
              {online ? 'Mentor online' : 'Mentor offline'}
            </span>
          </div>
          <div className="flex h-7 w-7 items-center justify-center rounded-full border border-[#26282E] bg-[#16171B] font-mono text-xs font-semibold text-[#FF6B2B]">
            OP
          </div>
        </div>
      </div>
    </header>
  )
}

/* ================================================================== */
/* Mode selection grid                                                 */
/* ================================================================== */

function ModeCard({
  mode,
  selected,
  onSelect,
  compact,
}: {
  mode: MentorMode
  selected: boolean
  onSelect: () => void
  compact?: boolean
}) {
  const meta = MODE_META[mode]
  const Icon = meta.icon
  return (
    <button
      onClick={onSelect}
      className={`group flex items-start gap-3 rounded-lg border text-left transition-all ${
        compact ? 'p-3' : 'flex-col items-start gap-2.5 p-4'
      } ${
        selected
          ? 'border-[#FF5B00] bg-[#1a150f] shadow-[0_0_0_1px_rgba(255,91,0,0.35),0_8px_30px_-12px_rgba(255,91,0,0.35)]'
          : 'border-[#22242A] bg-[#121316] hover:border-[#383b44] hover:bg-[#16171B]'
      }`}
    >
      <span
        className={`flex shrink-0 items-center justify-center rounded-md ${
          compact ? 'h-8 w-8' : 'h-9 w-9'
        } ${
          selected ? 'bg-[#FF5B00] text-[#070709]' : 'bg-[#1a1c20] text-[#FF6B2B] group-hover:bg-[#221811]'
        }`}
      >
        <Icon size={compact ? 16 : 18} strokeWidth={2} />
      </span>
      {compact ? (
        <span className="min-w-0 flex-1">
          <span className="block text-[13px] font-semibold text-white">{meta.label}</span>
          <span className="mt-0.5 block text-xs leading-snug text-[#8a91a0]">{meta.desc}</span>
        </span>
      ) : (
        <>
          <span className="text-sm font-semibold text-white">{meta.label}</span>
          <span className="text-xs leading-snug text-[#8a91a0]">{meta.desc}</span>
        </>
      )}
    </button>
  )
}

function ModeGrid({ mode, onSelect, compact }: { mode: MentorMode; onSelect: (m: MentorMode) => void; compact?: boolean }) {
  const order: MentorMode[] = ['explain', 'error_finder', 'generate', 'optimize', 'repo_report']
  return (
    <div className={`grid w-full gap-2.5 ${compact ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3'}`}>
      {order.map((m) => (
        <ModeCard key={m} mode={m} selected={m === mode} onSelect={() => onSelect(m)} compact={compact} />
      ))}
    </div>
  )
}

/* ================================================================== */
/* Chat / transcript view                                              */
/* ================================================================== */

function UserBubble({ turn }: { turn: ChatTurn }) {
  const modeName =
    turn.mode && MODE_META[turn.mode as MentorMode] ? MODE_META[turn.mode as MentorMode].label : turn.mode
  const lang = turn.language && turn.mode !== 'repo_report' ? turn.language.toUpperCase() : ''
  return (
    <div className="flex justify-end">
      <div className="max-w-[82%]">
        <div className="mb-1 flex items-center gap-2">
          {modeName && (
            <span className="rounded bg-[#FF5B00]/15 px-2 py-0.5 font-mono text-[10px] text-[#FF6B2B]">
              {modeName}
            </span>
          )}
          {lang && (
            <span className="rounded bg-[#1a1c20] px-2 py-0.5 font-mono text-[10px] text-[#8a91a0]">{lang}</span>
          )}
        </div>
        <div className="whitespace-pre-wrap rounded-lg rounded-tr-sm border border-[#3a3025] bg-[#1c170f] px-4 py-3 text-sm leading-relaxed text-[#e6e8ee]">
          {turn.content}
        </div>
      </div>
    </div>
  )
}

function AssistantBubble({ turn }: { turn: ChatTurn }) {
  const html = marked.parse(turn.content || '', { async: false }) as string
  return (
    <div className="flex justify-start">
      <div className="max-w-[88%]">
        <div className="mb-1 flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded bg-[#FF5B00] text-[#070709]">
            <Bot size={12} strokeWidth={2.4} />
          </span>
          <span className="font-mono text-[10px] tracking-widest text-[#8a91a0]">MENTOR</span>
        </div>
        <div className="rounded-lg rounded-tl-sm border border-[#22242A] bg-[#121316] px-4 py-3">
          <div className="mentor-markdown text-sm leading-relaxed text-[#dfe2ea]" dangerouslySetInnerHTML={{ __html: html }} />
          {(turn.model || turn.cost !== undefined || turn.duration_ms) && (
            <div className="mentor-scroll mt-3 flex flex-wrap gap-1.5 border-t border-[#1a1c20] pt-2.5">
              {turn.model && (
                <span className="rounded bg-[#1a1c20] px-1.5 py-0.5 font-mono text-[10px] text-[#8a91a0]">
                  {turn.model}
                </span>
              )}
              {turn.duration_ms !== undefined && (
                <span className="rounded bg-[#1a1c20] px-1.5 py-0.5 font-mono text-[10px] text-[#8a91a0]">
                  {(turn.duration_ms / 1000).toFixed(1)}s
                </span>
              )}
              {turn.cost !== undefined && (
                <span className="rounded bg-[#0c1410] px-1.5 py-0.5 font-mono text-[10px] text-[#10B981]">
                  est. {fmtCost(turn.cost)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ErrorBubble({ message }: { message: string }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[88%] rounded-lg border border-[#5b2126] bg-[#170a0c] px-4 py-3 text-sm text-[#ff9b9b]">
        {message}
      </div>
    </div>
  )
}

function ThinkingBubble() {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-[#22242A] bg-[#121316] px-4 py-3">
      <div className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#FF5B00] [animation-delay:0ms]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#FF5B00] [animation-delay:120ms]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#FF5B00] [animation-delay:240ms]" />
      </div>
      <span className="text-sm text-[#8a91a0]">Processing…</span>
    </div>
  )
}

function ChatTranscript({
  turns,
  busy,
  mode,
  hasContent,
  onSelectMode,
}: {
  turns: ChatTurn[]
  busy: boolean
  mode: MentorMode
  hasContent: boolean
  onSelectMode: (m: MentorMode) => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [turns, busy])

  if (!hasContent && turns.length === 0) {
    const meta = MODE_META[mode]
    const Icon = meta.icon
    return (
      <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col items-center justify-center gap-5 px-5 py-8 text-center lg:px-6">
        <span className="flex items-center gap-2 rounded border border-[#22242A] bg-[#121316] px-3 py-1 font-mono text-[11px] tracking-[0.2em] text-[#FF6B2B]">
          <Terminal size={12} /> YUKTI / AI
        </span>
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-white lg:text-2xl">Ready to review your code.</h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-[#8a91a0]">
            Pick a mentor mode or start typing your request directly.
          </p>
        </div>
        <ModeGrid mode={mode} onSelect={onSelectMode} compact />
      </div>
    )
  }

  return (
    <div ref={ref} className="mentor-scroll flex h-full flex-col gap-4 overflow-y-auto px-4 py-5 lg:px-6">
      {turns.map((turn, i) =>
        turn.role === 'user' ? (
          <UserBubble key={i} turn={turn} />
        ) : (
          <AssistantBubble key={i} turn={turn} />
        ),
      )}
      {busy && <ThinkingBubble />}
    </div>
  )
}

/* ================================================================== */
/* Floating command console / input dock                               */
/* ================================================================== */

function Dropdown({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
  disabled?: boolean
}) {
  return (
    <label className="flex cursor-pointer items-center gap-1.5 rounded-md border border-[#22242A] bg-[#0b0c0f] px-2.5 py-1.5 transition-colors hover:border-[#383b44]">
      <span className="text-[10px] text-[#5a6070]">{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="cursor-pointer appearance-none bg-transparent pr-4 font-mono text-xs text-[#dfe2ea] outline-none disabled:opacity-50"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value} className="bg-[#121316] text-white">
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown size={13} className="pointer-events-none -ml-3 text-[#5a6070]" />
    </label>
  )
}

function Composer({
  mode,
  language,
  model,
  onModeChange,
  onLanguageChange,
  onModelChange,
  value,
  onChange,
  onSubmit,
  busy,
}: {
  mode: MentorMode
  language: string
  model: string
  onModeChange: (m: MentorMode) => void
  onLanguageChange: (v: string) => void
  onModelChange: (v: string) => void
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  busy: boolean
}) {
  const areaRef = useRef<HTMLTextAreaElement>(null)
  const isRepo = mode === 'repo_report'
  const placeholder = isRepo
    ? 'Enter the absolute path of a repository folder on this machine (e.g. C:\\Users\\you\\my-project)...'
    : '> Paste code or type your request here...'

  const autoGrow = () => {
    const el = areaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }

  useEffect(autoGrow, [value])

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className="sticky bottom-4 z-20 px-3 pb-3 lg:px-6">
      <div className="mx-auto overflow-hidden rounded-xl border border-[#26282E] bg-[#0d0e12]/95 shadow-[0_16px_50px_-15px_rgba(0,0,0,0.75)] backdrop-blur">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2 border-b border-[#1E2025] px-3 py-1.5">
          <Dropdown label="LANG" value={language} options={LANGUAGES} onChange={onLanguageChange} disabled={isRepo} />
          <Dropdown label="MODEL" value={model} options={MODELS} onChange={onModelChange} />
          <div className="ml-auto flex items-center gap-1">
            <button
              className="flex items-center gap-1.5 rounded border border-[#22242A] bg-[#0b0c0f] px-2 py-1 text-xs text-[#8a91a0] transition-colors hover:border-[#383b44] hover:text-white"
              title="Attach file"
            >
              <Braces size={14} />
              <span className="hidden sm:inline">Attach</span>
            </button>
          </div>
        </div>

        {/* Textarea */}
        <div className="flex items-start gap-3 px-4 py-2.5">
          <span className="font-mono text-lg leading-6 text-[#FF5B00]">&gt;</span>
          <textarea
            ref={areaRef}
            rows={1}
            value={value}
            disabled={busy}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKey}
            placeholder={placeholder}
            aria-label="Message"
            className="mentor-scroll min-h-[24px] w-full resize-none bg-transparent font-mono text-sm leading-6 text-[#e6e8ee] outline-none placeholder:text-[#4a4f59] disabled:opacity-60"
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-[#1E2025] px-4 py-2">
          <span className="hidden items-center gap-1.5 font-mono text-[10px] text-[#5a6070] sm:flex">
            <kbd className="rounded border border-[#2a2c33] bg-[#0b0c0f] px-1.5 py-0.5">Ctrl</kbd>
            <span>+</span>
            <kbd className="rounded border border-[#2a2c33] bg-[#0b0c0f] px-1.5 py-0.5">Enter</kbd>
            <span className="ml-1 text-[#4a4f59]">to send · local-first, no code execution</span>
          </span>
          <button
            onClick={onSubmit}
            disabled={busy || !value.trim()}
            className="ml-auto flex items-center gap-1.5 rounded-md bg-[#FF5B00] px-3.5 py-1.5 text-sm font-semibold text-[#070709] transition-all hover:bg-[#FF6B2B] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send size={14} strokeWidth={2.4} />
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

/* ================================================================== */
/* Usage Analytics view (frontend-only, from /stats)                   */
/* ================================================================== */

function CodeMentorAnalytics({ stats }: { stats: Stats | null }) {
  const totals = stats?.totals

  const statCards = [
    { label: 'Sessions', value: fmtInt(totals?.sessions), icon: <Sparkles size={15} /> },
    { label: 'Turns', value: fmtInt(totals?.turns), icon: <Coins size={15} /> },
    { label: 'Tokens', value: fmtInt(totals?.total_tokens), icon: <Coins size={15} /> },
    { label: 'Cost', value: fmtCost(totals?.cost), icon: <Coins size={15} /> },
  ]

  const modes = stats?.by_mode ?? []
  const days = stats?.by_day ?? []
  const maxMode = modes.reduce((acc, m) => Math.max(acc, m.tokens), 0)
  const maxDay = days.reduce((acc, d) => Math.max(acc, d.tokens), 0)

  return (
    <div className="mentor-scroll min-h-0 flex-1 overflow-y-auto px-4 py-5 lg:px-6">
      <div className="mx-auto max-w-6xl">
        <div className="mb-4 flex items-center gap-2">
          <h1 className="text-[15px] font-semibold text-white">Usage Analytics</h1>
          <span className="rounded border border-[#2A2D34] px-1.5 py-px font-mono text-[10px] text-[#8A91A0]">
            YUKTI
          </span>
        </div>

        <div className="mb-5 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          {statCards.map((c) => (
            <div key={c.label} className="rounded-lg border border-[#22242A] bg-[#0d0e12] p-3.5">
              <div className="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B7280]">
                {c.icon}
                {c.label}
              </div>
              <div className="text-xl font-semibold text-white">{c.value}</div>
            </div>
          ))}
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <Card title="By mode">
            {modes.length === 0 ? (
              <Empty text="No per-mode data yet." />
            ) : (
              <div className="space-y-2.5">
                {modes.map((m) => (
                  <BarRow key={m.name} label={m.name} value={m.tokens} max={maxMode} />
                ))}
              </div>
            )}
          </Card>

          <Card title="By day">
            {days.length === 0 ? (
              <Empty text="No per-day data yet." />
            ) : (
              <div className="space-y-2.5">
                {days.map((d) => (
                  <BarRow key={d.day} label={d.day} value={d.tokens} max={maxDay} />
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 rounded-lg border border-[#22242A] bg-[#0d0e12] p-4">
      <div className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B7280]">{title}</div>
      {children}
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-[#2A2D34] py-12 text-center">
      <Coins size={24} className="mb-2 text-[#2A2D34]" />
      <p className="text-sm text-[#8A91A0]">{text}</p>
    </div>
  )
}

function BarRow({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[12px]">
        <span className="truncate text-[#C2C5CC]">{label}</span>
        <span className="shrink-0 font-mono text-[11px] text-[#8A91A0]">{fmtInt(value)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[#17181C]">
        <div className="h-full rounded-full bg-gradient-to-r from-[#FF5B00] to-[#FF8A4D]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

/* ================================================================== */
/* Root component                                                      */
/* ================================================================== */

export default function CodeMentorPlayground({ onExitApp }: { onExitApp?: (tab: string) => void }) {
  const [online, setOnline] = useState(true)
  const [activeTab, setActiveTab] = useState('Playground')

  const [mode, setMode] = useState<MentorMode>('explain')
  const [language, setLanguage] = useState('python')
  const [model, setModel] = useState('default')
  const [input, setInput] = useState('')

  const [currentSessionId, setCurrentSessionId] = useState('')
  const [stats, setStats] = useState<Stats | null>(null)

  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const hasContent = turns.length > 0

  /* ---------- initialize from URL (?mode=...) ---------- */
  useEffect(() => {
    const map: Record<string, MentorMode> = {
      explain: 'explain',
      error_finder: 'error_finder',
      errors: 'error_finder',
      generate: 'generate',
      optimize: 'optimize',
      repo: 'repo_report',
      repo_report: 'repo_report',
    }
    const q = new URLSearchParams(window.location.search).get('mode')
    if (q && map[q]) setMode(map[q])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /* ---------- health ---------- */
  useEffect(() => {
    const check = () => {
      fetch(`${API_BASE}/health`)
        .then((r) => setOnline(r.ok))
        .catch(() => setOnline(false))
    }
    check()
    const id = window.setInterval(check, 15000)
    return () => window.clearInterval(id)
  }, [])

  /* ---------- load stats ---------- */
  const load = async () => {
    try {
      const stRes = await fetch(`${API_BASE}/stats`)
      if (stRes.ok) {
        const data = await stRes.json()
        setStats(data)
      }
    } catch {
      setOnline(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /* ---------- new session ---------- */
  const handleNew = () => {
    setCurrentSessionId('')
    setTurns([])
    setInput('')
    setError('')
    load()
  }

  /* ---------- submit ---------- */
  const handleSubmit = async () => {
    const content = input.trim()
    if (!content || busy) return

    setBusy(true)
    setInput('')
    setError('')
    const userTurn: ChatTurn = { role: 'user', content, mode, language, timestamp: Date.now() / 1000 }
    setTurns((prev) => [...prev, userTurn])

    const payload = { mode, language, input_text: content, session_id: currentSessionId, model }
    try {
      const res = await fetch(`${API_BASE}/mentor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(`Error (${res.status}): ` + (data.detail || 'Unable to get a response.'))
        setTurns((prev) => prev.filter((t) => t !== userTurn))
        return
      }
      const assistantTurn: ChatTurn = {
        role: 'assistant',
        content: data.result || 'No response returned.',
        input_check: data.input_check,
        model: data.model,
        cost: data.cost,
        duration_ms: data.duration_ms,
        timestamp: Date.now() / 1000,
      }
      setCurrentSessionId(data.session_id || currentSessionId)
      setTurns((prev) => [...prev, assistantTurn])
      load()
    } catch (e) {
      setError('Error: ' + (e as Error).message)
      setTurns((prev) => prev.filter((t) => t !== userTurn))
    } finally {
      setBusy(false)
    }
  }

  /* ---------- select mode → focus input ---------- */
  const selectMode = (m: MentorMode) => {
    setMode(m)
    setActiveTab('Playground')
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#070709] text-white">
      <CursorGlow />
      <TopNav online={online} />

      <div className="flex min-h-0 flex-1">
        <PlaygroundSidebar
          mode={mode}
          activeView={activeTab}
          onSelectMode={selectMode}
          onNavigate={setActiveTab}
          onNewSession={handleNew}
          stats={stats}
          online={online}
        />

        {/* Main canvas */}
        <main className="relative flex min-h-0 flex-1 flex-col">
          {activeTab === 'History' ? (
            <RecentSessionsPage />
          ) : activeTab === 'Analytics' ? (
            <CodeMentorAnalytics stats={stats} />
          ) : (
            <>
              <div className="mentor-scroll flex-1 overflow-y-auto">
                <ChatTranscript turns={turns} busy={busy} mode={mode} hasContent={hasContent} onSelectMode={selectMode} />

                {error && (
                  <div className="px-4 pb-2">
                    <ErrorBubble message={error} />
                  </div>
                )}
              </div>

              <Composer
                mode={mode}
                language={language}
                model={model}
                onModeChange={setMode}
                onLanguageChange={setLanguage}
                onModelChange={setModel}
                value={input}
                onChange={setInput}
                onSubmit={handleSubmit}
                busy={busy}
              />
            </>
          )}
        </main>
      </div>
    </div>
  )
}
