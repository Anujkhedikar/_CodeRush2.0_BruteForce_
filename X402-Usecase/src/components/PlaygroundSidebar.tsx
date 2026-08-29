import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  ChartBar,
  ChevronLeft,
  ChevronRight,
  Code2,
  Coins,
  Folder,
  GitBranch,
  History,
  Menu,
  Plus,
  Settings,
  Sparkles,
  Zap,
} from 'lucide-react'
import type { Stats } from './CodeMentorPlayground'

/* ------------------------------------------------------------------ */
/* Shared types / helpers                                              */
/* ------------------------------------------------------------------ */

export type MentorMode = 'explain' | 'error_finder' | 'generate' | 'optimize' | 'repo_report'

export type SidebarStats = Stats | null

const MODE_ITEMS: { id: MentorMode; label: string; icon: typeof Sparkles }[] = [
  { id: 'explain', label: 'Explain', icon: Code2 },
  { id: 'error_finder', label: 'Find Errors', icon: AlertTriangle },
  { id: 'generate', label: 'Generate', icon: Sparkles },
  { id: 'optimize', label: 'Optimize', icon: Zap },
  { id: 'repo_report', label: 'Repo Report', icon: GitBranch },
]

/* ------------------------------------------------------------------ */
/* Viewport hook (responsive: expanded / compact / mobile drawer)      */
/* ------------------------------------------------------------------ */

type Viewport = { isMobile: boolean; isCompactRange: boolean }

function useViewport(): Viewport {
  const [viewport, setViewport] = useState<Viewport>(() => compute())
  function compute(): Viewport {
    const w = typeof window === 'undefined' ? 1440 : window.innerWidth
    return { isMobile: w < 768, isCompactRange: w >= 768 && w < 1200 }
  }
  useEffect(() => {
    const onResize = () => setViewport(compute())
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return viewport
}

function fmtInt(v: number | null | undefined): string {
  return v === null || v === undefined ? '0' : Number(v).toLocaleString('en-US')
}

function fmtCost(c: number | null | undefined): string {
  if (c === null || c === undefined) return '$0.00'
  return c >= 0.01 ? `$${c.toFixed(3)}` : `$${c.toFixed(4)}`
}

/* ------------------------------------------------------------------ */
/* Primitives                                                          */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/* Header: logo + name + collapse toggle                               */
/* ------------------------------------------------------------------ */

function SidebarHeader({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <div className="flex h-14 shrink-0 items-center border-b border-[#1C1E23] px-3">
      {!collapsed ? (
        <button
          onClick={onToggle}
          className="ml-auto shrink-0 rounded p-1.5 text-[#8A91A0] transition hover:bg-[#17181C] hover:text-white"
          aria-label="Collapse sidebar"
          title="Collapse sidebar"
        >
          <ChevronLeft size={16} />
        </button>
      ) : (
        <button
          onClick={onToggle}
          className="ml-auto shrink-0 rounded p-1.5 text-[#8A91A0] transition hover:bg-[#17181C] hover:text-white"
          aria-label="Expand sidebar"
          title="Expand sidebar"
        >
          <ChevronRight size={16} />
        </button>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* New Session button                                                  */
/* ------------------------------------------------------------------ */

function NewSessionButton({ collapsed, onClick }: { collapsed: boolean; onClick: () => void }) {
  return (
    <div className="shrink-0 px-3 pt-2.5">
      <button
        onClick={onClick}
        title={collapsed ? 'New session' : undefined}
        className="group flex h-11 w-full items-center gap-2 rounded-lg border border-[#26282E] bg-[#121318] px-3 text-[13px] font-medium text-[#E6E8EC] transition-colors hover:border-[#FF6B2B]/50 hover:bg-[#17181C] hover:text-white"
      >
        <Plus size={15} strokeWidth={2.4} className="shrink-0 text-[#FF6B2B]" />
        {!collapsed && <span className="truncate">{collapsed ? '' : 'New Session'}</span>}
      </button>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Workspace navigation (YUKTI-level views)                       */
/* ------------------------------------------------------------------ */

const WORKSPACE_ITEMS: { id: string; label: string; icon: typeof History }[] = [
  { id: 'History', label: 'History', icon: History },
  { id: 'Analytics', label: 'Analytics', icon: ChartBar },
]

function WorkspaceNavigation({
  activeView,
  collapsed,
  onNavigate,
}: {
  activeView: string
  collapsed: boolean
  onNavigate: (view: string) => void
}) {
  return (
    <nav className="shrink-0 px-2 pt-3">
      <div className="hidden pb-1 pl-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B7280] lg:block">
        Workspace
      </div>
      <div className="flex w-full flex-col gap-0.5">
        {WORKSPACE_ITEMS.map(({ id, label, icon: Icon }) => {
          const active = id === activeView
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              title={collapsed ? label : undefined}
              aria-label={label}
              aria-current={active ? 'true' : undefined}
              className={`group relative flex h-[42px] items-center gap-2.5 rounded-md text-left transition-colors ${
                collapsed ? 'justify-center px-0' : 'px-2.5'
              } ${active ? 'bg-[#1A1713] text-[#FF8A4D]' : 'text-[#C2C5CC] hover:bg-[#121318] hover:text-white'}`}
            >
              {active && <span className="absolute left-0 top-1.5 h-[30px] w-0.5 rounded-r bg-[#FF5B00]" />}
              <Icon
                size={16}
                strokeWidth={active ? 2.3 : 2}
                className={`shrink-0 ${active ? 'text-[#FF6B2B]' : 'text-[#8A91A0]'}`}
              />
              {!collapsed && <span className="truncate text-[13px] font-medium">{label}</span>}
            </button>
          )
        })}
      </div>
    </nav>
  )
}

/* ------------------------------------------------------------------ */
/* Mentor navigation                                                   */
/* ------------------------------------------------------------------ */

function MentorNavigation({
  mode,
  collapsed,
  onSelectMode,
}: {
  mode: MentorMode
  collapsed: boolean
  onSelectMode: (m: MentorMode) => void
}) {
  return (
    <nav className="shrink-0 px-2 pt-3">
      <div className="hidden pb-1 pl-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B7280] lg:block">
        Mentor
      </div>
      <div className="flex w-full flex-col gap-0.5">
        {MODE_ITEMS.map(({ id, label, icon: Icon }) => {
          const active = id === mode
          return (
            <button
              key={id}
              onClick={() => onSelectMode(id)}
              title={collapsed ? label : undefined}
              aria-label={label}
              aria-current={active ? 'true' : undefined}
              className={`group relative flex h-[42px] items-center gap-2.5 rounded-md text-left transition-colors ${
                collapsed ? 'justify-center px-0' : 'px-2.5'
              } ${active ? 'bg-[#1A1713] text-[#FF8A4D]' : 'text-[#C2C5CC] hover:bg-[#121318] hover:text-white'}`}
            >
              {active && <span className="absolute left-0 top-1.5 h-[30px] w-0.5 rounded-r bg-[#FF5B00]" />}
              <Icon
                size={16}
                strokeWidth={active ? 2.3 : 2}
                className={`shrink-0 ${active ? 'text-[#FF6B2B]' : 'text-[#8A91A0]'}`}
              />
              {!collapsed && <span className="truncate text-[13px] font-medium">{label}</span>}
            </button>
          )
        })}
      </div>
    </nav>
  )
}

/* ------------------------------------------------------------------ */
/* Repository context (compact, separate from sessions)                */
/* ------------------------------------------------------------------ */

function RepositoryContext({ collapsed }: { collapsed: boolean }) {
  if (collapsed) return null
  return (
    <div className="shrink-0 border-t border-[#1C1E23] px-3 pb-2.5 pt-2.5">
      <div className="flex items-center gap-1.5 pb-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B7280]">
        <Folder size={11} />
        Repository
      </div>
      <div className="flex items-center gap-2 rounded-md border border-[#23262C] bg-[#0E0F12] p-2">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[#17181C] text-[#FF6B2B]">
          <GitBranch size={14} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[12.5px] font-medium text-white">CodeRush2.0</p>
          <p className="truncate font-mono text-[10px] text-[#7A808C]">main · 42 files · scanned 2m ago</p>
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Footer: compact usage + settings                                    */
/* ------------------------------------------------------------------ */

function SidebarFooter({
  stats,
  online,
  collapsed,
}: {
  stats: SidebarStats
  online: boolean
  collapsed: boolean
}) {
  const totals = stats?.totals
  if (collapsed) {
    return (
      <div className="flex shrink-0 flex-col items-center gap-1 border-t border-[#1C1E23] py-3">
        <span title="Usage" className="flex h-9 w-9 items-center justify-center rounded-md text-[#8A91A0] hover:bg-[#17181C] hover:text-white">
          <Coins size={16} />
        </span>
        <span title="Settings" className="flex h-9 w-9 items-center justify-center rounded-md text-[#8A91A0] hover:bg-[#17181C] hover:text-white">
          <Settings size={16} />
        </span>
      </div>
    )
  }
  return (
    <div className="shrink-0 border-t border-[#1C1E23] px-3 py-2.5">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B7280]">Usage</span>
        <span
          className={`flex items-center gap-1 font-mono text-[9px] ${online ? 'text-[#10B981]' : 'text-[#FF5B00]'}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${online ? 'bg-[#10B981]' : 'bg-[#FF5B00]'}`} />
          {online ? 'LIVE' : 'OFFLINE'}
        </span>
      </div>
      <div className="flex items-center justify-between rounded-md border border-[#23262C] bg-[#0E0F12] px-2.5 py-1.5 font-mono text-[11px]">
        <span className="flex items-center gap-1.5 text-[#C2C5CC]">
          <Coins size={12} className="text-[#8A91A0]" />
          {fmtInt(totals?.total_tokens)} tokens
        </span>
        <span className="font-semibold text-[#FF8A4D]">{fmtCost(totals?.cost)}</span>
      </div>
      <button className="mt-1 flex w-full items-center gap-2 rounded-md px-1 py-1 text-left text-[11px] text-[#8A91A0] transition hover:text-white">
        <Settings size={12} />
        Settings
      </button>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Root sidebar                                                        */
/* ------------------------------------------------------------------ */

export default function PlaygroundSidebar({
  mode,
  activeView,
  onSelectMode,
  onNavigate,
  onNewSession,
  stats,
  online,
}: {
  mode: MentorMode
  activeView: string
  onSelectMode: (m: MentorMode) => void
  onNavigate: (view: string) => void
  onNewSession: () => void
  stats: SidebarStats
  online: boolean
}) {
  const { isMobile } = useViewport()
  const [collapsed, setCollapsed] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Expanded by default everywhere (no forced icon rail); collapse is a
  // manual toggle. Mobile shows an expanded drawer overlay.
  const forceCollapsed = isMobile ? false : collapsed

  return (
    <>
      {isMobile && drawerOpen && (
        <div className="fixed inset-0 z-40 bg-black/60" onClick={() => setDrawerOpen(false)} aria-hidden="true" />
      )}

      <aside
        className={`flex h-full flex-col overflow-hidden border-r border-[#1C1E23] bg-[#0A0B0E] text-[#E6E8EC] transition-[width] duration-300 ${
          isMobile ? 'fixed bottom-0 left-0 top-0 z-50' : 'shrink-0'
        } ${forceCollapsed ? 'w-16' : 'w-[262px]'} ${
          isMobile ? (drawerOpen ? 'translate-x-0' : '-translate-x-full') : 'translate-x-0'
        }`}
      >
        <SidebarHeader collapsed={forceCollapsed} onToggle={() => setCollapsed((c) => !c)} />
        <NewSessionButton
          collapsed={forceCollapsed}
          onClick={() => {
            onNewSession()
            if (isMobile) setDrawerOpen(false)
          }}
        />
        <MentorNavigation
          mode={mode}
          collapsed={forceCollapsed}
          onSelectMode={(m) => {
            onSelectMode(m)
            onNavigate('Playground')
            if (isMobile) setDrawerOpen(false)
          }}
        />
        <WorkspaceNavigation
          activeView={activeView}
          collapsed={forceCollapsed}
          onNavigate={(view) => {
            onNavigate(view)
            if (isMobile) setDrawerOpen(false)
          }}
        />

        <div className="flex-1" />

        {/* Fixed bottom: repository + usage (both separate & compact) */}
        <RepositoryContext collapsed={forceCollapsed} />
        <SidebarFooter stats={stats} online={online} collapsed={forceCollapsed} />
      </aside>

      {isMobile && (
        <button
          onClick={() => setDrawerOpen(true)}
          className="fixed bottom-5 left-4 z-30 flex h-11 w-11 items-center justify-center rounded-lg border border-[#23262C] bg-[#141519] text-white shadow-lg transition hover:bg-[#1C1E24]"
          aria-label="Open sidebar"
        >
          <Menu size={18} />
        </button>
      )}
    </>
  )
}
