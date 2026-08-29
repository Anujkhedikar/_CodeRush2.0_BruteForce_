import { useEffect, useRef } from 'react'

export default function CursorGlow() {
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let raf = 0
    let x = -275
    let y = -275
    let visible = false

    const frame = () => {
      raf = 0
      el.style.opacity = visible ? '1' : '0'
      el.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`
    }
    const schedule = () => {
      if (!raf) raf = requestAnimationFrame(frame)
    }

    const onMove = (e: MouseEvent) => {
      x = e.clientX
      y = e.clientY
      visible = true
      schedule()
    }
    const onLeave = () => {
      visible = false
      schedule()
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    document.documentElement.addEventListener('mouseleave', onLeave)

    return () => {
      window.removeEventListener('mousemove', onMove)
      document.documentElement.removeEventListener('mouseleave', onLeave)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div
      ref={ref}
      aria-hidden="true"
      className="pointer-events-none fixed left-0 top-0 z-40 rounded-full opacity-0"
      style={{
        width: 550,
        height: 550,
        background:
          'radial-gradient(circle, rgba(255,91,0,0.14) 0%, rgba(255,91,0,0.04) 45%, transparent 70%)',
        willChange: 'transform',
        transition: 'opacity 0.3s ease',
      }}
    />
  )
}