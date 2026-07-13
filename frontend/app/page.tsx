export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 px-6 text-center">
      <div className="max-w-4xl rounded-2xl border border-slate-800 bg-slate-900/70 p-10 shadow-2xl shadow-black/40">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.35em] text-cyan-400">Enterprise RAG Platform</p>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-6xl">
          Multi-tenant AI knowledge infrastructure for the modern enterprise.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
          Built with a modular FastAPI backend, a Next.js control plane, and deployment-ready infrastructure for Docker, Kubernetes, and CI/CD.
        </p>
      </div>
    </main>
  )
}
