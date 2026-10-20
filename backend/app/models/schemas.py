from typing import Optional
from pydantic import BaseModel, Field

# ==========================================
# Shared Health & Upload Schemas
# ==========================================

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    modules: list[str] = ["rag", "translate", "meeting"]
    providers: dict[str, str]

class UploadedFileResponse(BaseModel):
    id: str
    name: str
    mimeType: str
    size: int
    status: str = "ready"
    module: Optional[str] = None

class UploadResponse(BaseModel):
    files: list[UploadedFileResponse]


# ==========================================
# Tool 2: Institutional RAG Schemas
# ==========================================

class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    fileIds: list[str] = Field(..., min_length=1)

class CollectionResponse(BaseModel):
    id: str
    name: str
    status: str # "uploading" | "extracting" | "indexing" | "ready" | "failed"
    fileCount: int = 0
    chunkCount: int = 0
    embeddingProvider: Optional[str] = None
    embeddingDim: Optional[int] = None
    error: Optional[str] = None

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)

class Citation(BaseModel):
    fileId: str
    name: str
    page: Optional[int] = None
    section: Optional[str] = None
    excerpt: str

class QuestionResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    evidenceFound: bool = True
    providerUsed: Optional[str] = None


# ==========================================
# Tool 4: IndicTranslate Schemas
# ==========================================

class CreateTranslationJobRequest(BaseModel):
    fileIds: list[str] = []
    sourceText: Optional[str] = None
    sourceLanguage: str
    targetLanguage: str

class TranslationSegment(BaseModel):
    id: str
    source: str
    translated: str
    reviewFlag: str = "unreviewed" # "unreviewed" | "approved" | "edited"
    confidence: float = 1.0

class TranslationJobResponse(BaseModel):
    id: str
    status: str # "queued" | "processing" | "completed" | "failed"
    sourceLanguage: str
    targetLanguage: str
    segments: list[TranslationSegment] = []
    limitations: list[str] = [
        "Machine translation draft. Human review required before institutional publication."
    ]
    error: Optional[str] = None
    providerUsed: Optional[str] = None

class UpdateSegmentRequest(BaseModel):
    translated: str
    reviewFlag: str = "edited"


# ==========================================
# Tool 5: Meeting Minutes Schemas
# ==========================================

class CreateMeetingJobRequest(BaseModel):
    transcriptFileIds: list[str] = []
    audioFileIds: list[str] = []
    meetingTitle: Optional[str] = None

class DiscussionTopic(BaseModel):
    topic: str
    points: list[str] = []
    timestamp: Optional[str] = None

class MeetingDecision(BaseModel):
    decision: str
    status: str = "agreed" # "agreed" | "pending"
    evidence: Optional[str] = None

class ActionItem(BaseModel):
    task: str
    owner: Optional[str] = None
    dueDate: Optional[str] = None
    uncertain: bool = False

class MeetingDraft(BaseModel):
    title: str = "Meeting Record · Draft"
    summary: str
    discussions: list[DiscussionTopic] = []
    decisions: list[MeetingDecision] = []
    actionItems: list[ActionItem] = []
    uncertainties: list[str] = []

class MeetingJobResponse(BaseModel):
    id: str
    status: str # "queued" | "processing" | "completed" | "failed"
    source: str = "transcript" # "transcript" | "audio" | "hybrid"
    draft: Optional[MeetingDraft] = None
    limitations: list[str] = [
        "Generated draft requires human review. Action owners and deadlines are included only when explicitly stated in source."
    ]
    error: Optional[str] = None
    providerUsed: Optional[str] = None

class UpdateMeetingDraftRequest(BaseModel):
    draft: MeetingDraft
