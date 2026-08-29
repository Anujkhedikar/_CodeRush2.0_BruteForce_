import React, { useEffect, useState } from 'react'
import {
  ShieldCheck,
  ArrowRight,
  Sun,
  Moon,
  Star,
  MapPin,
  Lock,
  Zap,
  Crosshair,
  Radio,
  CheckCircle2,
  Droplets,
  Layers,
  Clock,
  BadgeCheck,
} from 'lucide-react'

/**
 * TacticalHero
 * ------------------------------------------------------------------
 * High-fidelity, tactical cyber-industrial dark-mode landing hero.
 *
 * Theme tokens (safety orange + terminal emerald on near-black):
 *   Canvas            #070709 / #0B0C0E
 *   Surface           #121316 / #16171B
 *   Border            #26282E
 *   Primary orange    #FF5B00 / #FF6B2B
 *   Terminal green    #10B981 / #00E599
 *
 * Deps: Tailwind CSS (JIT via the `content` glob) + `lucide-react`.
 *       Install with: `npm install lucide-react`
 *
 * The hero is fully self-contained. Render it wherever you like:
 *   <TacticalHero />
 * ------------------------------------------------------------------
 */

/* ============================ Data ============================ */

const NAV_LINKS = ['Find Pros', 'Telemetry', 'FAQ', 'How it Works']

// Simulated live logs shown inside the dispatch terminal ticker.
const LOG_MESSAGES = [
  'geo-fence: [zone-07] scan complete · 3 pros nearby',
  'union.listener: heartbeat OK · latency 42ms',
  'otp.vault: session locked · key rotation synced',
  'dispatch: matched PRO-2241 for request @ 12m',
  'insurance.ledger: policy AWS-9921 verified',
  'telemetry: rating delta +0.02 · integrity intact',
]

const METRICS = [
  { key: 'RESPONSE', value: '< 15 mins', unit: 'avg' },
  { key: 'SECURE OTP', value: 'ACTIVE', accent: true },
  { key: 'PRO RATING', value: '4.92 ★', unit: 'avg' },
]

const DATA_ROWS = [
  { label: 'Sector Status', value: 'ONLINE', accent: 'green' },
  { label: 'Hourly Rate', value: '$69.00 / HR', accent: 'none' },
  { label: 'Dispatch ETA', value: '12 mins away', accent: 'orange' },
]

/* ============================ Pieces ============================ */

const PaletteBackground: React.FC = () => (
  <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
    {/* Orange radial ambient glow */}
    <div
      className="absolute inset-0"
      style={{
        background:
          'radial-gradient(900px 520px at 78% -8%, rgba(255,91,0,0.08), transparent 62%), radial-gradient(600px 400px at -6% 108%, rgba(16,185,129,0.05), transparent 55%)',
      }}
    />
    {/* Faint dot-matrix grid overlay */}
    <div
      className="absolute inset-0"
      style={{
        backgroundImage: 'radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px)',
        backgroundSize: '24px 24px',
      }}
    />
  </div>
)

const BrandMark: React.FC = () => (
  <div className="flex shrink-0 items-center gap-2.5">
    <span className="grid h-9 w-9 place-items-center rounded-lg border border-[#26282E] bg-[#16171B] text-[#FF6B2B] shadow-[0_0_18px_rgba(255,107,43,0.25)]">
      <Zap size={18} strokeWidth={2.2} />
    </span>
    <span className="text-[17px] font-bold tracking-tight text-white">
      Pro<span className="text-[#FF6B2B]">Link</span>
    </span>
  </div>
)

const NavigationBar: React.FC = () => {
  const [dark, setDark] = useState(true)
  return (
    <header className="flex items-center justify-between gap-4 border-b border-[#1A1C21] px-6 py-4 backdrop-blur-sm lg:px-12">
      <BrandMark />

      <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
        {NAV_LINKS.map((label) => (
          <a
            key={label}
            href="#"
            className="rounded-md px-3 py-2 text-sm font-medium text-neutral-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            {label}
          </a>
        ))}
      </nav>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setDark((d) => !d)}
          aria-label="Toggle theme"
          className="grid h-9 w-9 place-items-center rounded-md border border-[#26282E] text-neutral-300 transition-colors hover:text-white"
        >
          {dark ? <Sun size={17} /> : <Moon size={17} />}
        </button>
        <a href="#" className="hidden text-sm font-medium text-neutral-300 transition-colors hover:text-white sm:block">
          Sign In
        </a>
        <a
          href="#"
          className="rounded-full bg-gradient-to-r from-[#FF5B00] to-[#FF6B2B] px-4 py-2 text-sm font-semibold text-black shadow-[0_0_22px_rgba(255,107,43,0.45)] transition hover:brightness-110"
        >
          Get Covered
        </a>
      </div>
    </header>
  )
}

const MicroBadge: React.FC = () => (
  <div className="inline-flex items-center gap-2 rounded-full border border-[#FF6B2B]/35 bg-[#FF6B2B]/10 px-3.5 py-1.5 font-mono text-[11px] font-medium tracking-[0.14em] text-[#FF8A4D]">
    <ShieldCheck size={13} />
    [VERIFIED &amp; INSURED PRO INFRASTRUCTURE]
  </div>
)

const TerminalTicker: React.FC = () => {
  const [line, setLine] = useState(LOG_MESSAGES[0])

  useEffect(() => {
    let i = 0
    const id = window.setInterval(() => {
      i = (i + 1) % LOG_MESSAGES.length
      setLine(LOG_MESSAGES[i])
    }, 2600)
    return () => window.clearInterval(id)
  }, [])

  return (
    <div className="mt-8 flex w-full max-w-xl items-center gap-3 overflow-hidden rounded-lg border border-[#26282E] bg-[#0B0C0E] px-4 py-3">
      <span className="font-mono text-[#00E599]">&gt;_</span>
      <span className="truncate font-mono text-xs text-neutral-300">
        DISPATCH LISTENER ACTIVE : <span className="text-[#00E599]">{line}</span>
      </span>
      <span className="ml-auto inline-flex shrink-0 items-center gap-1.5 rounded-full border border-[#10B981]/40 bg-[#10B981]/10 px-2.5 py-0.5 font-mono text-[10px] font-medium tracking-wider text-[#00E599]">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#00E599]" />
        SYNCED
      </span>
    </div>
  )
}

const MetricReadout: React.FC<{ item: (typeof METRICS)[number] }> = ({ item }) => (
  <div className="flex flex-col">
    <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-neutral-500">{item.key}</span>
    <span className={`mt-1 text-base font-semibold ${item.accent ? 'text-[#00E599]' : 'text-white'}`}>
      {item.value}
    </span>
    {item.unit && <span className="text-[11px] text-neutral-500">{item.unit}</span>}
  </div>
)

const MetricsBar: React.FC = () => (
  <div className="mt-9 flex w-full max-w-xl items-center gap-8 border-t border-[#1A1C21] pt-5">
    {METRICS.map((m) => (
      <React.Fragment key={m.key}>
        <MetricReadout item={m} />
      </React.Fragment>
    ))}
  </div>
)

/* ---- Telemetry card (right) ---- */

const DataRow: React.FC<{ label: string; value: string; accent?: 'green' | 'orange' | 'none' }> = ({
  label,
  value,
  accent = 'none',
}) => {
  const valueColor =
    accent === 'green' ? 'text-[#00E599]' : accent === 'orange' ? 'text-[#FF6B2B]' : 'text-white'
  return (
    <div className="flex items-center justify-between rounded-lg border border-[#1C1E24] bg-[#16171B] px-3.5 py-3">
      <span className="font-mono text-[11px] uppercase tracking-wider text-neutral-400">{label}</span>
      <span className={`flex items-center gap-1.5 font-mono text-sm font-semibold ${valueColor}`}>
        {accent === 'green' && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#00E599]" />}
        {value}
      </span>
    </div>
  )
}

const TelemetryCard: React.FC = () => (
  <div className="relative w-full max-w-[380px] rounded-2xl border border-[#26282E] bg-[#121316]/95 p-6 shadow-[0_40px_90px_-30px_rgba(0,0,0,0.8),0_0_50px_rgba(255,91,0,0.08)] backdrop-blur-md">
    {/* Floating status tags */}
    <div className="flex items-center justify-between px-1">
      <span className="rounded-md border border-[#10B981]/40 bg-[#10B981]/10 px-2 py-1 font-mono text-[10px] tracking-wider text-[#00E599]">
        VERIFIED LICENSED
      </span>
      <span className="rounded-md border border-[#FF6B2B]/40 bg-[#FF6B2B]/10 px-2 py-1 font-mono text-[10px] tracking-wider text-[#FF8A4D]">
        PRO OPERATIONAL
      </span>
    </div>

    {/* Profile */}
    <div className="mt-5 flex items-center gap-3.5">
      <span className="grid h-14 w-14 shrink-0 place-items-center rounded-xl border border-[#FF6B2B]/40 bg-gradient-to-br from-[#FF6B2B]/25 to-transparent font-mono text-lg font-bold text-[#FF8A4D]">
        JS
      </span>
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-lg font-semibold text-white">Jordan S.</span>
          <BadgeCheck size={16} className="shrink-0 text-[#00E599]" />
        </div>
        <p className="text-sm text-neutral-400">Licensed HVAC Tech · 8 yrs</p>
      </div>
    </div>

    {/* Data grid */}
    <div className="mt-5 grid gap-2.5">
      <DataRow label="Sector Status" value="ONLINE" accent="green" />
      <DataRow label="Hourly Rate" value="$69.00 / HR" />
      <DataRow label="Dispatch ETA" value="12 mins away" accent="orange" />
    </div>

    {/* Rating row */}
    <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-[#1C1E24] bg-[#16171B] px-3.5 py-3">
      <div className="flex items-center gap-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <Star key={i} size={14} className={i < 5 ? 'fill-[#FF6B2B] text-[#FF6B2B]' : 'text-neutral-600'} />
        ))}
        <span className="ml-1.5 font-mono text-xs text-neutral-300">4.92</span>
      </div>
      <span className="ml-auto inline-flex items-center gap-1 rounded-md border border-[#FF6B2B]/40 bg-[#FF6B2B]/10 px-2 py-0.5 font-mono text-[10px] tracking-wider text-[#FF8A4D]">
        <Zap size={11} />
        SAME-DAY
      </span>
      <span className="inline-flex items-center gap-1 rounded-md border border-[#10B981]/40 bg-[#10B981]/10 px-2 py-0.5 font-mono text-[10px] tracking-wider text-[#00E599]">
        <ShieldCheck size={11} />
        INSURED
      </span>
    </div>

    {/* Primary action */}
    <button
      type="button"
      className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#FF5B00] to-[#FF6B2B] py-3.5 text-sm font-bold tracking-wide text-black shadow-[0_0_28px_rgba(255,107,43,0.5)] transition hover:brightness-110"
    >
      INITIATE BOOKING
      <ArrowRight size={17} />
    </button>

    {/* Footer status */}
    <div className="mt-4 flex items-center gap-3 border-t border-[#1C1E24] pt-4">
      <Lock size={14} className="text-[#00E599]" />
      <span className="font-mono text-[11px] text-neutral-400">SECURE GATEWAY</span>
      <span className="font-mono text-[11px] text-neutral-500">#7F-2A1-C</span>
      <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-[#10B981]/40 bg-[#10B981]/10 px-2.5 py-1 font-mono text-[10px] font-medium tracking-wider text-[#00E599]">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#00E599]" />
        GPS DISPATCH ACTIVE
      </span>
    </div>
  </div>
)

/* ============================ Hero ============================ */

const TacticalHero: React.FC = () => (
  <section className="page-hero relative min-h-screen overflow-hidden bg-[#070709] text-neutral-200 selection:bg-[#FF6B2B] selection:text-black">
    <PaletteBackground />

    <NavigationBar />

    <div className="mx-auto grid w-full max-w-7xl grid-cols-1 items-center gap-12 px-6 py-14 lg:grid-cols-[1.05fr_0.95fr] lg:px-12 lg:py-20">
      {/* Left: hero copy */}
      <div className="relative z-10 animate-fade-up">
        <MicroBadge />

        <h1 className="mt-6 text-5xl font-extrabold leading-[1.02] tracking-tight text-white sm:text-6xl xl:text-7xl">
          The Right Help,
          <br />
          <span className="bg-gradient-to-r from-[#FF8A4D] via-[#FF6B2B] to-[#FF5B00] bg-clip-text text-transparent drop-shadow-[0_0_24px_rgba(255,107,43,0.4)]">
            Right Near You
          </span>
        </h1>

        <p className="mt-6 max-w-xl text-lg leading-relaxed text-neutral-400">
          Real-time telemetry matches verified, locally-vetted pros to your exact request — with live
          dispatch status, transparent hourly rates, and insured coverage on every booking.
        </p>

        <div className="mt-8 flex flex-wrap items-center gap-4">
          <a
            href="#"
            className="group inline-flex items-center gap-2.5 rounded-full bg-gradient-to-r from-[#FF5B00] to-[#FF6B2B] px-6 py-3.5 text-sm font-bold text-black shadow-[0_0_30px_rgba(255,107,43,0.5)] transition hover:brightness-110"
          >
            Find Your Pro Now
            <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
          </a>
          <a
            href="#"
            className="inline-flex items-center gap-2 rounded-full border border-[#26282E] bg-transparent px-6 py-3.5 text-sm font-medium text-neutral-200 transition-colors hover:bg-white/5 hover:text-white"
          >
            <MapPin size={17} className="text-[#FF6B2B]" />
            Track Live Dispatch
          </a>
        </div>

        <TerminalTicker />
        <MetricsBar />
      </div>

      {/* Right: telemetry card */}
      <div className="relative z-10 flex justify-center lg:justify-end">
        <div className="animate-float">
          <TelemetryCard />
        </div>
        {/* floating decorative icons */}
        <Crosshair size={22} color="#FF6B2B" className="absolute left-0 top-6 hidden animate-pulse lg:block" />
        <Radio size={18} color="#00E599" className="absolute bottom-10 left-4 hidden animate-pulse lg:block" />
        <Clock size={18} color="#00E599" className="absolute right-2 top-2 hidden animate-pulse lg:block" />
      </div>
    </div>

    {/* Bottom footer strip */}
    <div className="relative z-10 border-t border-[#1A1C21]">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-4 text-[11px] font-mono text-neutral-500 lg:px-12">
        <span className="inline-flex items-center gap-2">
          <Droplets size={13} className="text-[#FF6B2B]" />
          TRACKED · REAL-TIME TELEMETRY
        </span>
        <span className="inline-flex items-center gap-2">
          <CheckCircle2 size={13} className="text-[#00E599]" />
          100% VERIFIED &amp; INSURED PROS
        </span>
        <span className="inline-flex items-center gap-2">
          <Layers size={13} className="text-[#FF6B2B]" />
          ECOSYSTEM v2.4 · SCAN COMPLETE
        </span>
      </div>
    </div>
  </section>
)

export default TacticalHero

/* Note: `.animate-fade-up` and `.animate-float` keyframes live in src/styles/main.css */
