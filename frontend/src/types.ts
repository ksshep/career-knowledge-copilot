export type DocumentStatus = 'processing' | 'ready' | 'failed'

export interface DocumentItem {
  id: string
  filename: string
  size_bytes: number
  status: DocumentStatus
}

export interface DocumentListResponse {
  items: DocumentItem[]
}

export interface Citation {
  filename: string
  page_number: number
  chunk_index: number
}

export interface AskResponse {
  answer: string
  citations: Citation[]
  has_evidence: boolean
}
