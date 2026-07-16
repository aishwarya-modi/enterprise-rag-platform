export interface RAGQueryRequest {
  query: string
  tenant_id?: string
  provider?: string
  model?: string
  max_retries?: number
}

export interface Citation {
  source: string
  page: number
  excerpt: string
}

export interface RAGQueryResponse {
  answer: string
  citations: Citation[]
  rewritten_query: string
  step_history: string[]
  status: string
  provider: string
  model: string
}

export type StreamEventType =
  | 'stream_start'
  | 'step_start'
  | 'step_complete'
  | 'token'
  | 'citation'
  | 'answer_complete'
  | 'stream_complete'
  | 'error'
  | 'aborted'

export interface StreamEvent {
  event: StreamEventType
  id?: string
  data: Record<string, unknown>
}

export interface StreamTokenData {
  node: string
  token: string
  field: 'rewritten_query' | 'compressed_context' | 'answer'
}

export interface StreamStepData {
  node: string
  message?: string
  rewritten_query?: string
  document_count?: number
  ranked_count?: number
  citation_count?: number
  error?: string
}

export interface StreamCitationData {
  citation: Citation
}

export interface StreamCompleteData {
  query_id: string
  status: 'completed' | 'failed'
  answer: string
  citations: Citation[]
  step_history: string[]
  rewritten_query: string
  provider: string
  model: string
}

export interface StreamStartData {
  query_id: string
  query: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchRAGQuery(request: RAGQueryRequest): Promise<RAGQueryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/rag/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function abortQuery(queryId: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/rag/query/${queryId}/abort`, {
    method: 'POST',
  })
}

export function createStreamConnection(
  request: RAGQueryRequest,
  onEvent: (event: StreamEvent) => void,
  onError: (error: Event | Error) => void,
): { abort: () => void; queryIdPromise: Promise<string> } {
  const controller = new AbortController()

  let resolveQueryId: (id: string) => void
  const queryIdPromise = new Promise<string>((resolve) => {
    resolveQueryId = resolve
  })

  const body = JSON.stringify({
    query: request.query,
    tenant_id: request.tenant_id || 'default',
    provider: request.provider || 'openai',
    model: request.model || 'gpt-4o-mini',
    max_retries: request.max_retries ?? 2,
  })

  fetch(`${API_BASE}/api/v1/rag/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: res.statusText }))
        onError(new Error(error.detail || `Stream request failed: ${res.status}`))
        return
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()!

        let currentEvent = ''
        let currentId: string | undefined
        let currentData = ''

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim()
          } else if (line.startsWith('id:')) {
            currentId = line.slice(3).trim()
          } else if (line.startsWith('data:')) {
            currentData = line.slice(5).trim()
          } else if (line.trim() === '' && currentEvent && currentData) {
            try {
              const data = JSON.parse(currentData)
              const event: StreamEvent = { event: currentEvent as StreamEventType, data, id: currentId }
              if (currentEvent === 'stream_start' && data.query_id) {
                resolveQueryId(data.query_id)
              }
              onEvent(event)
            } catch {
              onEvent({ event: currentEvent as StreamEventType, data: { raw: currentData } })
            }
            currentEvent = ''
            currentId = undefined
            currentData = ''
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err instanceof Error ? err : new Error(String(err)))
      }
    })

  return {
    abort: () => controller.abort(),
    queryIdPromise,
  }
}
