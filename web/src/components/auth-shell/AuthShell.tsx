import { CheckCircle2, Compass, GitBranch, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

type AuthShellProps = {
  eyebrow: string
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
}

const highlights = [
  {
    icon: Compass,
    title: 'Plan with clarity',
    description: 'Turn releases into focused versions and actionable todos.',
  },
  {
    icon: GitBranch,
    title: 'Stay close to the work',
    description: 'Keep roadmap tasks aligned with GitHub issues and branches.',
  },
  {
    icon: CheckCircle2,
    title: 'Ship with confidence',
    description: 'See what is ready, in progress, complete, and released.',
  },
]

export function AuthShell({
  eyebrow,
  title,
  description,
  children,
  footer,
}: AuthShellProps) {
  return (
    <main className="grid min-h-dvh bg-canvas lg:grid-cols-[minmax(22rem,0.9fr)_minmax(30rem,1.1fr)]">
      <aside className="relative hidden overflow-hidden bg-slate-950 p-10 text-white lg:flex lg:flex-col xl:p-14">
        <div
          aria-hidden="true"
          className="absolute -top-32 -left-24 size-96 rounded-full bg-accent/30 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="absolute right-[-8rem] bottom-[-8rem] size-96 rounded-full bg-cyan-500/20 blur-3xl"
        />

        <Link
          to="/"
          className="relative z-10 inline-flex w-fit items-center gap-3 text-lg font-black tracking-[-0.03em] text-white no-underline focus-visible:outline-3 focus-visible:outline-offset-4 focus-visible:outline-white"
        >
          <span className="grid size-10 place-items-center rounded-xl bg-white/10 ring-1 ring-white/15">
            <Sparkles aria-hidden="true" size={20} strokeWidth={2.2} />
          </span>
          Northstar
        </Link>

        <div className="relative z-10 my-auto max-w-lg py-14">
          <p className="m-0 text-xs font-bold tracking-[0.14em] text-cyan-300 uppercase">
            Project delivery, connected
          </p>
          <h2 className="mt-4 mb-0 text-4xl font-black tracking-[-0.045em] text-balance xl:text-5xl">
            From first idea to released roadmap.
          </h2>
          <p className="mt-5 mb-0 max-w-md text-base leading-7 text-slate-300">
            Give your team one calm place to plan versions, coordinate work,
            and move every project forward.
          </p>

          <ul className="mt-10 grid list-none gap-5 p-0">
            {highlights.map(({ icon: Icon, title, description }) => (
              <li key={title} className="flex items-start gap-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/10 text-cyan-300 ring-1 ring-white/10">
                  <Icon aria-hidden="true" size={18} strokeWidth={2.2} />
                </span>
                <div>
                  <p className="m-0 text-sm font-bold text-white">{title}</p>
                  <p className="mt-1 mb-0 text-sm leading-5 text-slate-400">
                    {description}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative z-10 m-0 text-xs text-slate-500">
          Thoughtful project operations for teams that ship.
        </p>
      </aside>

      <section className="flex min-w-0 items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
        <div className="w-full max-w-xl">
          <Link
            to="/"
            className="mb-10 inline-flex items-center gap-2 text-base font-black tracking-[-0.03em] text-heading no-underline focus-visible:outline-3 focus-visible:outline-offset-4 focus-visible:outline-focus lg:hidden"
          >
            <span className="grid size-9 place-items-center rounded-xl bg-accent text-white">
              <Sparkles aria-hidden="true" size={18} strokeWidth={2.2} />
            </span>
            Northstar
          </Link>

          <p className="m-0 text-xs font-bold tracking-[0.14em] text-accent uppercase">
            {eyebrow}
          </p>
          <h1 className="mt-3 mb-0 text-3xl font-black tracking-[-0.04em] text-heading sm:text-4xl">
            {title}
          </h1>
          <p className="mt-3 mb-0 max-w-lg text-sm leading-6 text-muted sm:text-base">
            {description}
          </p>

          <div className="mt-8">{children}</div>
          {footer && <div className="mt-7">{footer}</div>}
        </div>
      </section>
    </main>
  )
}
