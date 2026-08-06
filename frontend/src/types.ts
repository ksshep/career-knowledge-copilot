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
