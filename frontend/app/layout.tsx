import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Enterprise RAG Platform',
  description: 'Production-grade enterprise retrieval augmented generation platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased">{children}</body>
    </html>
  )
}
