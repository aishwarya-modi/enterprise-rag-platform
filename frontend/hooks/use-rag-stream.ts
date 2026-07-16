'use client'

import { useCallback, useRef, useState } from 'react'

import {
  RAGQueryRequest,
  StreamEvent,
  StreamTokenData,
  StreamStepData,
  StreamCitationData,
  StreamCompleteData,
  StreamStartData,
  Citation,
  createStreamConnection,
  abortQuery,
} from '@/lib/rag-client'

export interface StreamStep {
  node: string
  message: string
  status: 'pending' | 'active' | 'complete'
}

export interface StreamState {
  isStreaming: boolean
  queryId: string | null
  answer: string
  rewrittenQuery: string
  citations: Citation[]
  steps: StreamStep[]
  currentField: string | null
  error: string | null
  aborted: boolean
}

export function useRAGStream() {
  const [state, setState] = useState<StreamState>({
    isStreaming: false,
    queryId: null,
    answer: '',
    rewrittenQuery: '',
    citations: [],
    steps: [],
    currentField: null,
    error: null,
    aborted: false,
  })

  const connectionAbortRef = useRef<(() => void) | null>(null)
  const queryIdRef = useRef<string | null>(null)

  const reset = useCallback(() => {
    connectionAbortRef.current?.()
    connectionAbortRef.current = null
    queryIdRef.current = null
    setState({
      isStreaming: false,
      queryId: null,
      answer: '',
      rewrittenQuery: '',
      citations: [],
      steps: [],
      currentField: null,
      error: null,
      aborted: false,
    })
  }, [])

  const startStream = useCallback(
    (request: RAGQueryRequest) => {
      reset()

      setState((prev) => ({ ...prev, isStreaming: true, error: null, aborted: false }))

      const nodeLabels: Record<string, string> = {
        rewrite_query: 'Rewriting query',
        retrieve_documents: 'Searching knowledge base',
        rerank_documents: 'Reranking results',
        compress_context: 'Compressing context',
        generate_answer: 'Generating answer',
        generate_citations: 'Extracting citations',
      }

      const { abort: connectionAbort, queryIdPromise } = createStreamConnection(
        request,
        (event: StreamEvent) => {
          switch (event.event) {
            case 'stream_start': {
              const data = event.data as unknown as StreamStartData
              queryIdRef.current = data.query_id
              setState((prev) => ({ ...prev, queryId: data.query_id }))
              break
            }
            case 'step_start': {
              const data = event.data as unknown as StreamStepData
              setState((prev) => ({
                ...prev,
                currentField: data.node,
                steps: [
                  ...prev.steps,
                  {
                    node: data.node,
                    message: data.message || nodeLabels[data.node] || data.node,
                    status: 'active',
                  },
                ],
              }))
              break
            }
            case 'step_complete': {
              const data = event.data as unknown as StreamStepData
              setState((prev) => ({
                ...prev,
                currentField: null,
                steps: prev.steps.map((s) =>
                  s.node === data.node ? { ...s, status: 'complete' as const } : s
                ),
              }))
              break
            }
            case 'token': {
              const data = event.data as unknown as StreamTokenData
              setState((prev) => {
                if (data.field === 'answer') {
                  return { ...prev, answer: prev.answer + data.token }
                }
                if (data.field === 'rewritten_query') {
                  return { ...prev, rewrittenQuery: prev.rewrittenQuery + data.token }
                }
                return prev
              })
              break
            }
            case 'citation': {
              const data = event.data as unknown as StreamCitationData
              setState((prev) => ({
                ...prev,
                citations: [...prev.citations, data.citation],
              }))
              break
            }
            case 'stream_complete': {
              const data = event.data as unknown as StreamCompleteData
              setState((prev) => ({
                ...prev,
                isStreaming: false,
                answer: data.answer || prev.answer,
                citations: data.citations?.length ? data.citations : prev.citations,
                steps: prev.steps.map((s) => ({ ...s, status: 'complete' as const })),
              }))
              break
            }
            case 'error': {
              setState((prev) => ({
                ...prev,
                isStreaming: false,
                error: (event.data as { error?: string }).error || 'Unknown error',
              }))
              break
            }
            case 'aborted': {
              setState((prev) => ({
                ...prev,
                isStreaming: false,
                aborted: true,
              }))
              break
            }
          }
        },
        () => {
          setState((prev) => ({
            ...prev,
            isStreaming: false,
            error: prev.error || 'Connection lost',
          }))
        },
      )

      connectionAbortRef.current = connectionAbort

      queryIdPromise.then((id) => {
        queryIdRef.current = id
      })

      return queryIdPromise
    },
    [reset],
  )

  const abort = useCallback(async () => {
    const queryId = queryIdRef.current
    if (queryId) {
      try {
        await abortQuery(queryId)
      } catch {
        // best effort
      }
    }
    connectionAbortRef.current?.()
    setState((prev) => ({
      ...prev,
      isStreaming: false,
      aborted: true,
    }))
  }, [])

  return {
    ...state,
    startStream,
    abort,
    reset,
  }
}
