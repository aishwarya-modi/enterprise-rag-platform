'use client'

import { StreamStep } from '@/hooks/use-rag-stream'
import { Citation } from '@/lib/rag-client'
import { CheckCircle2, Circle, Loader2, FileText, AlertCircle } from 'lucide-react'

interface MessageProps {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  isStreaming?: boolean
}

export function Message({ role, content, citations, isStreaming }: MessageProps) {
  const isUser = role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[85%] rounded-2xl px-5 py-3 ${
          isUser
            ? 'bg-cyan-600 text-white'
            : 'bg-slate-800 text-slate-100 border border-slate-700'
        }`}
      >
        <div className="whitespace-pre-wrap text-sm leading-relaxed">
          {content}
          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-0.5 bg-cyan-400 animate-pulse rounded-sm" />
          )}
        </div>
        {citations && citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-700">
            <p className="text-xs font-medium text-slate-400 mb-2">Sources</p>
            <div className="flex flex-wrap gap-2">
              {citations.map((citation, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 text-xs bg-slate-700/50 text-slate-300 rounded-md px-2 py-1"
                >
                  <FileText className="w-3 h-3" />
                  {citation.source}, p.{citation.page}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface StepIndicatorProps {
  steps: StreamStep[]
}

export function StepIndicator({ steps }: StepIndicatorProps) {
  if (steps.length === 0) return null

  return (
    <div className="mb-4 px-4">
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
        {steps.map((step, i) => (
          <div key={`${step.node}-${i}`} className="flex items-center gap-2 py-1">
            {step.status === 'complete' ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            ) : step.status === 'active' ? (
              <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin shrink-0" />
            ) : (
              <Circle className="w-3.5 h-3.5 text-slate-600 shrink-0" />
            )}
            <span
              className={`text-xs ${
                step.status === 'active'
                  ? 'text-cyan-300'
                  : step.status === 'complete'
                  ? 'text-slate-400'
                  : 'text-slate-600'
              }`}
            >
              {step.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

interface ErrorBannerProps {
  error: string
  onDismiss: () => void
}

export function ErrorBanner({ error, onDismiss }: ErrorBannerProps) {
  return (
    <div className="mx-4 mb-4 bg-red-950/50 border border-red-800/50 rounded-xl p-3 flex items-start gap-2">
      <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
      <span className="text-sm text-red-300 flex-1">{error}</span>
      <button
        onClick={onDismiss}
        className="text-red-400 hover:text-red-300 text-xs"
      >
        Dismiss
      </button>
    </div>
  )
}
