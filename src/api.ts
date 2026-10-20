export type UploadedFile = {
  id: string
  name: string
  mimeType: string
  size: number
  status: string
  module?: string
}

export type Collection = {
  id: string
  name: string
  status: 'uploading' | 'extracting' | 'indexing' | 'ready' | 'failed'
  fileCount: number
  chunkCount: number
  embeddingProvider?: string
  embeddingDim?: number
  error?: string
}

export type Citation = {
  fileId: string
  name: string
  page?: number
  section?: string
  excerpt: string
}

export type QuestionResponse = {
  answer: string
  citations: Citation[]
  evidenceFound: boolean
  providerUsed?: string
}

export type TranslationSegment = {
  id: string
  source: string
  translated: string
  reviewFlag: 'unreviewed' | 'approved' | 'edited' | 'no_model'
  confidence: number
}

export type TranslationJob = {
  id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  sourceLanguage: string
  targetLanguage: string
  segments: TranslationSegment[]
  limitations: string[]
  error?: string
  providerUsed?: string
}

export type DiscussionTopic = {
  topic: string
  points: string[]
  timestamp?: string
}

export type MeetingDecision = {
  decision: string
  status: 'agreed' | 'pending'
  evidence?: string
}

export type ActionItem = {
  task: string
  owner?: string | null
  dueDate?: string | null
  uncertain: boolean
}

export type MeetingDraft = {
  title: string
  summary: string
  discussions: DiscussionTopic[]
  decisions: MeetingDecision[]
  actionItems: ActionItem[]
  uncertainties: string[]
}

export type MeetingJob = {
  id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  source: 'transcript' | 'audio' | 'hybrid'
  draft?: MeetingDraft
  limitations: string[]
  error?: string
  providerUsed?: string
}

const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

async function safeFetch(url: string, options?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, options)
  } catch (err: any) {
    throw new Error(
      `Unable to reach the backend API. Please ensure the FastAPI backend is running on http://127.0.0.1:8000 (open a separate PowerShell window and run 'python run.py' inside the backend directory).`
    )
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `API request failed with status ${res.status}`
    try {
      const errData = await res.json()
      if (errData && errData.detail) {
        message = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail)
      }
    } catch {
      if (res.status === 502 || res.status === 503 || res.status === 504) {
        message = `Backend service is unreachable (502 Bad Gateway). Please verify that the FastAPI backend server is running at http://127.0.0.1:8000 (open a separate PowerShell window, run 'cd backend', then 'python run.py').`
      } else {
        message = res.statusText || message
      }
    }
    throw new Error(message)
  }
  return res.json()
}

export async function checkBackendHealth(): Promise<{ status: string; modules: string[] }> {
  const res = await safeFetch(`${API_BASE}/health`)
  return handleResponse(res)
}

export async function uploadFiles(files: File[], moduleName: string): Promise<UploadedFile[]> {
  const formData = new FormData()
  formData.append('module', moduleName)
  for (const file of files) {
    formData.append('files', file)
  }

  const res = await safeFetch(`${API_BASE}/uploads`, {
    method: 'POST',
    body: formData,
  })
  const data = await handleResponse<{ files: UploadedFile[] }>(res)
  return data.files
}

export async function createCollection(name: string, fileIds: string[]): Promise<Collection> {
  const res = await safeFetch(`${API_BASE}/rag/collections`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, fileIds }),
  })
  return handleResponse<Collection>(res)
}

export async function askQuestion(collectionId: string, question: string): Promise<QuestionResponse> {
  const res = await safeFetch(`${API_BASE}/rag/collections/${collectionId}/questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return handleResponse<QuestionResponse>(res)
}

export async function createTranslationJob(params: {
  fileIds?: string[]
  sourceText?: string
  sourceLanguage: string
  targetLanguage: string
}): Promise<TranslationJob> {
  const res = await safeFetch(`${API_BASE}/translate/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return handleResponse<TranslationJob>(res)
}

export async function getTranslationJob(jobId: string): Promise<TranslationJob> {
  const res = await safeFetch(`${API_BASE}/translate/jobs/${jobId}`)
  return handleResponse<TranslationJob>(res)
}

export async function updateTranslationSegment(
  jobId: string,
  segmentId: string,
  translated: string,
  reviewFlag: string = 'edited'
): Promise<TranslationJob> {
  const res = await safeFetch(`${API_BASE}/translate/jobs/${jobId}/segments/${segmentId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ translated, reviewFlag }),
  })
  return handleResponse<TranslationJob>(res)
}

export async function createMeetingJob(params: {
  transcriptFileIds?: string[]
  audioFileIds?: string[]
  meetingTitle?: string
}): Promise<MeetingJob> {
  const res = await safeFetch(`${API_BASE}/meetings/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return handleResponse<MeetingJob>(res)
}

export async function getMeetingJob(jobId: string): Promise<MeetingJob> {
  const res = await safeFetch(`${API_BASE}/meetings/jobs/${jobId}`)
  return handleResponse<MeetingJob>(res)
}

export async function getLatestMeetingJob(): Promise<MeetingJob | null> {
  try {
    const res = await safeFetch(`${API_BASE}/meetings/jobs/latest`)
    if (res.status === 404) return null
    return handleResponse<MeetingJob>(res)
  } catch {
    return null
  }
}

export async function updateMeetingDraft(jobId: string, draft: MeetingDraft): Promise<MeetingJob> {
  const res = await safeFetch(`${API_BASE}/meetings/jobs/${jobId}/draft`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ draft }),
  })
  return handleResponse<MeetingJob>(res)
}
