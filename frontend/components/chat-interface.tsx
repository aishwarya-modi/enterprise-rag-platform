'use client'

import { KeyboardEvent, useRef, useEffect, useState } from 'react'
import { useRAGStream } from '@/hooks/use-rag-stream'
import { Message, StepIndicator, ErrorBanner } from '@/components/message'
import { Send, Square, Trash2 } from 'lucide-react'

interface ChatEntry {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: { source: string; page: number; excerpt: string }[]
  isStreaming?: boolean
}

export function ChatInterface() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatEntry[]>([])
  const stream = useRAGStream()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [streamEntryId, setStreamEntryId] = useState<string | null>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, stream.answer])

  useEffect(() => {
    if (streamEntryId && stream.answer) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === streamEntryId
            ? { ...m, content: stream.answer, citations: stream.citations }
            : m
        )
      )
    }
  }, [stream.answer, stream.citations, streamEntryId])

  useEffect(() => {
    if (streamEntryId && !stream.isStreaming && stream.answer) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === streamEntryId
            ? { ...m, content: stream.answer, citations: stream.citations, isStreaming: false }
            : m
        )
      )
      setStreamEntryId(null)
    }
  }, [stream.isStreaming, stream.answer, stream.citations, streamEntryId])

  const handleSubmit = () => {
    const trimmed = input.trim()
    if (!trimmed || stream.isStreaming) return

    const userEntry: ChatEntry = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
    }
    const assistantEntry: ChatEntry = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      isStreaming: true,
    }

    setMessages((prev) => [...prev, userEntry, assistantEntry])
    setStreamEntryId(assistantEntry.id)
    setInput('')

    stream.startStream({ query: trimmed })
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleClear = () => {
    stream.reset()
    setMessages([])
    setStreamEntryId(null)
  }

  return (
    <div className="flex flex-col h-screen bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">R</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100">RAG Assistant</h1>
            <p className="text-xs text-slate-500">Enterprise Knowledge Search</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={handleClear}
            className="text-slate-500 hover:text-slate-300 transition-colors p-2 rounded-lg hover:bg-slate-800"
            title="Clear chat"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center mb-4">
              <span className="text-white font-bold text-xl">R</span>
            </div>
            <h2 className="text-lg font-medium text-slate-200 mb-1">Ask anything</h2>
            <p className="text-sm text-slate-500 max-w-sm">
              Query your enterprise knowledge base. Responses stream in real-time with source citations.
            </p>
          </div>
        )}

        <div className="max-w-3xl mx-auto">
          {messages.map((msg) => (
            <Message
              key={msg.id}
              role={msg.role}
              content={msg.content}
              citations={msg.citations}
              isStreaming={msg.isStreaming}
            />
          ))}
          {stream.isStreaming && <StepIndicator steps={stream.steps} />}
          {stream.error && (
            <ErrorBanner error={stream.error} onDismiss={stream.reset} />
          )}
          {stream.aborted && (
            <div className="text-center text-xs text-slate-500 py-2">
              Stream aborted
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="border-t border-slate-800 bg-slate-950 px-4 py-4 shrink-0">
        <div className="max-w-3xl mx-auto">
          <div className="relative flex items-end bg-slate-900 border border-slate-700 rounded-2xl focus-within:border-cyan-600 transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question..."
              rows={1}
              className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-500 px-4 py-3 outline-none resize-none max-h-32"
              style={{ minHeight: '44px' }}
            />
            <div className="flex items-center gap-1 pr-2 pb-2">
              {stream.isStreaming ? (
                <button
                  onClick={stream.abort}
                  className="p-2 rounded-xl bg-red-600 hover:bg-red-500 text-white transition-colors"
                  title="Stop generating"
                >
                  <Square className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={!input.trim()}
                  className="p-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-30 disabled:cursor-not-allowed text-white transition-colors"
                  title="Send message"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
          <p className="text-center text-xs text-slate-600 mt-2">
            Streaming responses with real-time citations
          </p>
        </div>
      </div>
    </div>
  )
}
