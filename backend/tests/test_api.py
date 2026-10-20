import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.storage import storage_service

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "rag" in data["modules"]
    assert "translate" in data["modules"]
    assert "meeting" in data["modules"]
    assert "providers" in data

def test_upload_valid_text_document():
    content = b"Institutional Policy Document.\n\nSection 1: Academic council approved the new admissions schedule."
    response = client.post(
        "/api/uploads",
        data={"module": "rag"},
        files={"files": ("policy.txt", content, "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 1
    assert data["files"][0]["name"] == "policy.txt"
    assert data["files"][0]["status"] == "ready"
    assert "id" in data["files"][0]

def test_upload_invalid_extension():
    content = b"echo 'hack'"
    response = client.post(
        "/api/uploads",
        data={"module": "rag"},
        files={"files": ("script.exe", content, "application/octet-stream")}
    )
    assert response.status_code == 400
    assert "not supported" in response.json()["detail"].lower()

def test_upload_corrupt_pdf():
    # Not starting with %PDF-
    bad_pdf = b"NOT_A_REAL_PDF_FILE"
    response = client.post(
        "/api/uploads",
        data={"module": "rag"},
        files={"files": ("corrupt.pdf", bad_pdf, "application/pdf")}
    )
    assert response.status_code == 400
    assert "not a valid pdf" in response.json()["detail"].lower()

def test_rag_workflow_with_evidence_and_no_evidence():
    # 1. Upload doc
    doc_text = (
        "Academic Council Regulations 2026.\n\n"
        "Section 4: The annual student admissions portal opens on July 15 and closes on August 30.\n\n"
        "Section 5: Fee payment must be completed within 14 days of admission confirmation."
    ).encode("utf-8")

    upload_res = client.post(
        "/api/uploads",
        data={"module": "rag"},
        files={"files": ("council_regulations.txt", doc_text, "text/plain")}
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["files"][0]["id"]

    # 2. Create collection
    col_res = client.post(
        "/api/rag/collections",
        json={"name": "Admissions Regulations", "fileIds": [file_id]}
    )
    assert col_res.status_code == 200
    col_data = col_res.json()
    col_id = col_data["id"]
    assert col_data["status"] == "ready"
    assert col_data["fileCount"] == 1
    assert col_data["chunkCount"] > 0

    # 3. Question with clear evidence in document
    q_res = client.post(
        f"/api/rag/collections/{col_id}/questions",
        json={"question": "When does the student admissions portal open?"}
    )
    assert q_res.status_code == 200
    ans_data = q_res.json()
    assert ans_data["evidenceFound"] is True
    assert "July 15" in ans_data["answer"] or "admissions" in ans_data["answer"].lower()
    assert len(ans_data["citations"]) > 0
    assert ans_data["citations"][0]["fileId"] == file_id

    # 4. Question with NO evidence in document
    no_ev_res = client.post(
        f"/api/rag/collections/{col_id}/questions",
        json={"question": "What is the quantum speed of the Mars rover spaceship?"}
    )
    assert no_ev_res.status_code == 200
    no_ev_data = no_ev_res.json()
    assert no_ev_data["evidenceFound"] is False
    assert "no sufficient evidence" in no_ev_data["answer"].lower()
    assert len(no_ev_data["citations"]) == 0

def test_upload_empty_file_rejected():
    response = client.post(
        "/api/uploads",
        data={"module": "rag"},
        files={"files": ("empty.txt", b"", "text/plain")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_rag_collection_isolation():
    """Verify that documents in Collection A are completely isolated from Collection B."""
    doc_a = b"Collection A Secret: The admissions committee convenes only on Wednesdays."
    doc_b = b"Collection B Information: Hostel room allocations are announced every Friday."

    up_a = client.post("/api/uploads", data={"module": "rag"}, files={"files": ("doc_a.txt", doc_a, "text/plain")})
    up_b = client.post("/api/uploads", data={"module": "rag"}, files={"files": ("doc_b.txt", doc_b, "text/plain")})
    assert up_a.status_code == 200 and up_b.status_code == 200
    id_a = up_a.json()["files"][0]["id"]
    id_b = up_b.json()["files"][0]["id"]

    col_a = client.post("/api/rag/collections", json={"name": "Admissions Col", "fileIds": [id_a]}).json()["id"]
    col_b = client.post("/api/rag/collections", json={"name": "Hostel Col", "fileIds": [id_b]}).json()["id"]

    # Query Col A for Col B's topic: must NOT find evidence
    cross_res = client.post(f"/api/rag/collections/{col_a}/questions", json={"question": "When are hostel room allocations announced?"})
    assert cross_res.status_code == 200
    assert cross_res.json()["evidenceFound"] is False
    assert len(cross_res.json()["citations"]) == 0

    # Query Col A for its own topic: must find evidence and cite doc_a only
    own_res = client.post(f"/api/rag/collections/{col_a}/questions", json={"question": "When does the admissions committee convene?"})
    assert own_res.status_code == 200
    assert own_res.json()["evidenceFound"] is True
    assert all(c["fileId"] == id_a for c in own_res.json()["citations"])

def test_rag_dimension_mismatch_rejection(monkeypatch):
    """Verify that querying a collection with an incompatible embedding vector dimension returns a clear 409 rejection."""
    doc = b"Admissions policy guidelines 2026."
    up = client.post("/api/uploads", data={"module": "rag"}, files={"files": ("guidelines.txt", doc, "text/plain")})
    assert up.status_code == 200
    fid = up.json()["files"][0]["id"]

    # Create collection using local 256-dim provider
    col_id = client.post("/api/rag/collections", json={"name": "Dimension Test Col", "fileIds": [fid]}).json()["id"]

    # Mock an incompatible embedding provider with 768 dimensions (simulating a provider change)
    from app.providers.embeddings import EmbeddingProvider
    class Mock768Provider(EmbeddingProvider):
        provider_name = "mock_provider"
        model_name = "mock-768"
        dimension = 768
        def embed_query(self, text: str):
            return [0.1] * 768
        def embed_documents(self, texts):
            return [[0.1] * 768 for _ in texts]

    monkeypatch.setattr("app.services.rag_service.get_embedding_provider", lambda: Mock768Provider())

    # Querying should reject with 409 Conflict rather than silently computing bad dot products or crashing
    q_res = client.post(f"/api/rag/collections/{col_id}/questions", json={"question": "What is the admissions policy?"})
    assert q_res.status_code == 409
    assert "mismatch" in q_res.json()["detail"].lower()
    assert "re-index" in q_res.json()["detail"].lower() or "rebuild" in q_res.json()["detail"].lower()

def test_indic_translate_language_validation():
    """Verify that unsupported languages and identical source/target languages are clearly rejected."""
    # 1. Identical source and target language
    same_res = client.post(
        "/api/translate/jobs",
        json={"sourceText": "Hello", "sourceLanguage": "English", "targetLanguage": "English"}
    )
    assert same_res.status_code == 400
    assert "identical" in same_res.json()["detail"].lower()

    # 2. Unsupported source language
    bad_src = client.post(
        "/api/translate/jobs",
        json={"sourceText": "Bonjour", "sourceLanguage": "French", "targetLanguage": "Tamil"}
    )
    assert bad_src.status_code == 400
    assert "not supported" in bad_src.json()["detail"].lower()

    # 3. Unsupported target language
    bad_tgt = client.post(
        "/api/translate/jobs",
        json={"sourceText": "Hello", "sourceLanguage": "English", "targetLanguage": "German"}
    )
    assert bad_tgt.status_code == 400
    assert "not supported" in bad_tgt.json()["detail"].lower()

def test_indic_translate_no_model_configured_returns_blank_draft(monkeypatch):
    """When no real translation model is configured, draft must be blank, labeled no_model, and allow manual entry."""
    from app.providers.translation import LocalTranslationProvider
    monkeypatch.setattr("app.services.translation_service.get_translation_provider", lambda: LocalTranslationProvider())

    sample_text = "New circular issued by the registrar regarding annual leave policies."

    # 1. POST /api/translate/jobs creates the job
    create_res = client.post(
        "/api/translate/jobs",
        json={
            "sourceText": sample_text,
            "sourceLanguage": "English",
            "targetLanguage": "Tamil"
        }
    )
    assert create_res.status_code == 200
    job_id = create_res.json()["id"]

    # 2. GET /api/translate/jobs/{job_id} fetches the result
    get_res = client.get(f"/api/translate/jobs/{job_id}")
    assert get_res.status_code == 200
    job_data = get_res.json()

    assert job_data["status"] == "completed"
    assert len(job_data["segments"]) > 0
    seg = job_data["segments"][0]
    # Translation must be blank because no neural model is configured (no fake glossary substitutions)
    assert seg["translated"] == "", "Unconfigured translation engine must return blank translated text"
    # reviewFlag clearly indicates no_model
    assert seg["reviewFlag"] == "no_model", f"Expected reviewFlag 'no_model', got '{seg['reviewFlag']}'"
    assert any("no translation model is configured" in lim.lower() for lim in job_data["limitations"])

    # 3. User can manually enter a draft for the blank segment
    manual_edit_res = client.put(
        f"/api/translate/jobs/{job_id}/segments/{seg['id']}",
        json={"translated": "பதிவாளர் வெளியிட்ட புதிய சுற்றறிக்கை.", "reviewFlag": "edited"}
    )
    assert manual_edit_res.status_code == 200
    edited_job = manual_edit_res.json()
    edited_seg = next(s for s in edited_job["segments"] if s["id"] == seg["id"])
    assert edited_seg["translated"] == "பதிவாளர் வெளியிட்ட புதிய சுற்றறிக்கை."
    assert edited_seg["reviewFlag"] == "edited"

def test_indic_translate_configured_model_path(monkeypatch):
    """When a real MT provider is configured, verify genuine translation output, reviewFlag='unreviewed', and human-in-the-loop workflow."""
    from app.providers.translation import TranslationProvider
    class MockNeuralTranslationProvider(TranslationProvider):
        def translate_segments(self, segments, source_lang, target_lang):
            # Returns real Tamil script translation
            return ["கல்விசார் மன்றம் புதிய கொள்கைக்கு ஒப்புதல் அளித்தது."]

    monkeypatch.setattr("app.services.translation_service.get_translation_provider", lambda: MockNeuralTranslationProvider())

    sample_text = "The academic council approved the new admissions policy for the institution."
    create_res = client.post(
        "/api/translate/jobs",
        json={"sourceText": sample_text, "sourceLanguage": "English", "targetLanguage": "Tamil"}
    )
    assert create_res.status_code == 200
    job = create_res.json()
    assert job["status"] == "completed"
    assert len(job["segments"]) == 1

    seg = job["segments"][0]
    # Distinguish genuine translation from blank, unchanged English, or glossary substitution
    assert seg["translated"] != "", "Configured model must return non-blank translation"
    assert seg["translated"] != sample_text, "Must not return unchanged source English"
    # Contains Tamil Unicode characters
    import re
    assert re.search(r"[\u0B80-\u0BFF]", seg["translated"]), "Must contain genuine Tamil script"
    # Must be marked unreviewed (requiring human review, never automatically approved)
    assert seg["reviewFlag"] == "unreviewed"
    assert seg["confidence"] > 0

    # User can approve or edit the machine draft
    approve_res = client.put(
        f"/api/translate/jobs/{job['id']}/segments/{seg['id']}",
        json={"translated": seg["translated"], "reviewFlag": "approved"}
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["segments"][0]["reviewFlag"] == "approved"


def test_meeting_minutes_workflow_transcript():
    transcript_text = (
        "Topic: Admissions Calendar Review.\n"
        "Alice: We are discussing the schedule for 2026 admissions.\n"
        "Bob: Decision: Academic council approved the revised timeline.\n"
        "Alice: Action item: Dr. Sharma will prepare the portal guidelines by next week.\n"
        "Charlie: Someone should also check the server bandwidth."
    ).encode("utf-8")

    upload_res = client.post(
        "/api/uploads",
        data={"module": "meeting"},
        files={"files": ("meeting_transcript.txt", transcript_text, "text/plain")}
    )
    assert upload_res.status_code == 200
    tf_id = upload_res.json()["files"][0]["id"]

    # Create meeting job
    job_res = client.post(
        "/api/meetings/jobs",
        json={"transcriptFileIds": [tf_id], "meetingTitle": "Council Meeting"}
    )
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["status"] == "completed"
    assert job_data["draft"] is not None
    draft = job_data["draft"]
    assert len(draft["decisions"]) > 0
    assert len(draft["actionItems"]) > 0
    # Verify uncertainty flag was set for items without explicit owner/date
    assert any(a["uncertain"] is True for a in draft["actionItems"])

def test_meeting_minutes_audio_unconfigured():
    # Synthetic WAV header
    wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    upload_res = client.post(
        "/api/uploads",
        data={"module": "meeting"},
        files={"files": ("recording.wav", wav_header, "audio/wav")}
    )
    assert upload_res.status_code == 200
    af_id = upload_res.json()["files"][0]["id"]

    # When AUDIO_PROVIDER=none, should cleanly fail with explanation rather than fake transcription
    job_res = client.post(
        "/api/meetings/jobs",
        json={"audioFileIds": [af_id]}
    )
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["status"] == "failed"
    assert "not configured" in job_data["error"].lower() or "whisper" in job_data["error"].lower()


def test_meeting_minutes_exact_transcript_extraction():
    """Regression test for the exact user-provided transcript.

    Transcript:
        Chair: We agreed to hold the workshop on 3 November 2026.
        Maya: I will book Room 2 by 25 October 2026.
        The team approved the budget of 15,000 rupees.

    Expected:
    - Action: "Book Room 2", owner="Maya", dueDate="25 October 2026", uncertain=False
    - Decision: budget approval of 15,000 rupees (status="agreed")
    - Decision: workshop agreement (status="agreed")
    - No generic "Review draft minutes" placeholder action
    - No "No explicit action assignments" uncertainty
    """
    transcript_text = (
        "Chair: We agreed to hold the workshop on 3 November 2026.\n"
        "Maya: I will book Room 2 by 25 October 2026.\n"
        "The team approved the budget of 15,000 rupees."
    ).encode("utf-8")

    upload_res = client.post(
        "/api/uploads",
        data={"module": "meeting"},
        files={"files": ("exact_meeting.txt", transcript_text, "text/plain")},
    )
    assert upload_res.status_code == 200
    tf_id = upload_res.json()["files"][0]["id"]

    job_res = client.post(
        "/api/meetings/jobs",
        json={"transcriptFileIds": [tf_id], "meetingTitle": "Workshop Planning"},
    )
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["status"] == "completed"
    draft = job_data["draft"]
    assert draft is not None

    # ── Action items ──────────────────────────────────────────────────
    assert len(draft["actionItems"]) >= 1, f"Expected ≥1 action items, got {draft['actionItems']}"
    book_action = draft["actionItems"][0]
    assert "book room 2" in book_action["task"].lower(), f"Task should contain 'Book Room 2', got: {book_action['task']}"
    assert book_action["owner"] == "Maya", f"Owner should be 'Maya', got: {book_action['owner']}"
    assert book_action["dueDate"] is not None, "Due date should not be None"
    assert "25 October 2026" in book_action["dueDate"] or "25 Oct" in book_action["dueDate"], \
        f"Due date should be '25 October 2026', got: {book_action['dueDate']}"
    assert book_action["uncertain"] is False, "uncertain should be False when owner and dueDate are both present"

    # No generic placeholder action
    for act in draft["actionItems"]:
        assert "review draft minutes" not in act["task"].lower(), \
            f"Generic fallback action should not appear: {act['task']}"

    # ── Decisions ─────────────────────────────────────────────────────
    decision_texts = " ".join(d["decision"].lower() for d in draft["decisions"])
    assert "15,000 rupees" in decision_texts or "budget" in decision_texts, \
        f"Budget approval decision missing. Decisions: {[d['decision'] for d in draft['decisions']]}"
    # All captured decisions should have status "agreed"
    for d in draft["decisions"]:
        assert d["status"] == "agreed", f"Decision status should be 'agreed', got: {d['status']}"

    # ── Uncertainties ─────────────────────────────────────────────────
    for u in draft.get("uncertainties", []):
        assert "no explicit action assignments" not in u.lower(), \
            f"Should not report 'no explicit action assignments': {u}"


def test_meeting_minutes_transcript_with_no_actions():
    """Verify that a transcript with no action assignments produces an empty action list without inventing actions."""
    transcript_text = (
        "Topic: General Information Sharing.\n"
        "Prof. Kumar: The department organized three technical seminars this semester.\n"
        "Dr. Varma: Attendance was high across all batches.\n"
        "Chair: Thank you everyone for the constructive update."
    ).encode("utf-8")

    upload_res = client.post(
        "/api/uploads",
        data={"module": "meeting"},
        files={"files": ("info_sharing.txt", transcript_text, "text/plain")},
    )
    assert upload_res.status_code == 200
    tf_id = upload_res.json()["files"][0]["id"]

    job_res = client.post(
        "/api/meetings/jobs",
        json={"transcriptFileIds": [tf_id], "meetingTitle": "Department Review"},
    )
    assert job_res.status_code == 200
    draft = job_res.json()["draft"]
    assert draft is not None
    # Must NOT invent action items or decisions
    assert len(draft["actionItems"]) == 0, f"Expected 0 action items, got: {draft['actionItems']}"
    assert len(draft["decisions"]) == 0, f"Expected 0 decisions, got: {draft['decisions']}"
    # Must preserve discussions
    assert len(draft["discussions"]) > 0


def test_error_handling_sanitizes_secrets():
    """Verify that backend error messages never leak API keys, system paths with secrets, or database credentials."""
    # Test an invalid collection query
    err_res = client.post("/api/rag/collections/non-existent-uuid/questions", json={"question": "Test?"})
    assert err_res.status_code == 404
    detail = str(err_res.json()["detail"])
    assert "AIza" not in detail
    assert "sk-" not in detail
    assert "password" not in detail.lower()
    assert "secret" not in detail.lower()


def test_meeting_minutes_longer_library_renovation_transcript():
    """Verify the realistic library renovation transcript extracts evidence-based summary,

    discussion topic groups, decisions, and action items with exact deadlines without inventing dates.
    """
    transcript_text = (
        "Chair: We need to review the library renovation before the next semester. The reading room is too noisy during afternoon study hours.\n"
        "Latha: Students asked for a quiet study zone and more charging points. We should consider moving the group tables near the entrance.\n"
        "Ravi: The facilities team can inspect the electrical outlets this week. I will send the inspection report by Friday.\n"
        "Chair: We agreed to create a quiet study zone in the east wing. The group tables will remain where they are until the facilities review is complete.\n"
        "Meena: I will collect student feedback and share a summary by 12 November 2026.\n"
        "Chair: The renovation budget is approved up to 2 lakh rupees, subject to the facilities report."
    ).encode("utf-8")

    upload_res = client.post(
        "/api/uploads",
        data={"module": "meeting"},
        files={"files": ("library_renovation.txt", transcript_text, "text/plain")},
    )
    assert upload_res.status_code == 200
    tf_id = upload_res.json()["files"][0]["id"]

    job_res = client.post(
        "/api/meetings/jobs",
        json={"transcriptFileIds": [tf_id], "meetingTitle": "Library Renovation Review"},
    )
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["status"] == "completed"
    draft = job_data["draft"]
    assert draft is not None

    # ── 1. Summary Evidence ───────────────────────────────────────────
    summary_lower = draft["summary"].lower()
    assert "library renovation" in summary_lower or "renovation" in summary_lower, "Summary must mention library renovation"
    assert "noise" in summary_lower or "noisy" in summary_lower or "quiet study" in summary_lower, "Summary must mention noise / quiet study zone"
    assert "facilities" in summary_lower, "Summary must mention facilities review/inspection"
    assert "budget" in summary_lower or "lakh" in summary_lower, "Summary must mention approved budget"

    # ── 2. Meaningful Discussion Topics ───────────────────────────────
    assert len(draft["discussions"]) >= 3, f"Expected at least 3 discussion topic groups, got {len(draft['discussions'])}"
    topics_text = " ".join(d["topic"].lower() for d in draft["discussions"])
    assert "renovation" in topics_text or "budget" in topics_text, "Discussion topic for renovation planning/budget missing"
    assert "quiet" in topics_text or "noise" in topics_text or "study zone" in topics_text, "Discussion topic for study zone/noise missing"
    assert "outlet" in topics_text or "facilities" in topics_text or "charging" in topics_text, "Discussion topic for electrical outlets missing"
    assert "table" in topics_text or "feedback" in topics_text, "Discussion topic for table placement/feedback missing"

    # Ensure points under topics contain actual statements
    all_points = [pt for d in draft["discussions"] for pt in d["points"]]
    assert any("reading room is too noisy" in pt.lower() for pt in all_points)
    assert any("charging points" in pt.lower() or "electrical outlets" in pt.lower() for pt in all_points)
    assert any("group tables" in pt.lower() for pt in all_points)

    # ── 3. Decisions ──────────────────────────────────────────────────
    assert len(draft["decisions"]) >= 3, f"Expected at least 3 decisions, got {len(draft['decisions'])}"
    decisions_text = " ".join(d["decision"].lower() for d in draft["decisions"])
    assert "quiet study zone" in decisions_text, "Decision on quiet study zone missing"
    assert "group tables will remain" in decisions_text or "remain where they are" in decisions_text, "Decision on keeping tables in place missing"
    assert "budget is approved" in decisions_text or "approved up to 2 lakh" in decisions_text, "Decision on budget approval missing"
    assert "facilities report" in decisions_text, "Condition 'subject to the facilities report' must be preserved"

    # ── 4. Action Items ───────────────────────────────────────────────
    assert len(draft["actionItems"]) == 2, f"Expected exactly 2 action items, got {len(draft['actionItems'])}"

    import re
    # Ravi's action
    ravi_act = next((a for a in draft["actionItems"] if a["owner"] == "Ravi"), None)
    assert ravi_act is not None, "Action item for Ravi missing"
    assert "inspection report" in ravi_act["task"].lower()
    assert ravi_act["dueDate"] is not None
    assert "friday" in ravi_act["dueDate"].lower(), f"Expected due date 'Friday', got {ravi_act['dueDate']}"
    # Verify Friday is preserved without fabricating an arbitrary calendar date
    assert not re.search(r"\b202\d-\d{2}-\d{2}\b", ravi_act["dueDate"]), "Should not fabricate calendar date for 'Friday'"
    assert ravi_act["uncertain"] is False

    # Meena's action
    meena_act = next((a for a in draft["actionItems"] if a["owner"] == "Meena"), None)
    assert meena_act is not None, "Action item for Meena missing"
    assert "feedback" in meena_act["task"].lower()
    assert meena_act["dueDate"] is not None
    assert "12 november 2026" in meena_act["dueDate"].lower()
    assert meena_act["uncertain"] is False


def test_meeting_minutes_pleasantries_only_zero_invented_content():
    """Verify that a transcript with only greetings and procedural pleasantries returns empty lists and no invented content."""
    transcript_text = (
        "Alice: Good morning everyone.\n"
        "Bob: Good morning Alice. Can everyone hear me?\n"
        "Charlie: Yes, loud and clear.\n"
        "Bob: Sounds good. Let's wait a minute.\n"
        "Alice: Thanks everyone."
    ).encode("utf-8")

    upload_res = client.post(
        "/api/uploads",
        data={"module": "meeting"},
        files={"files": ("pleasantries.txt", transcript_text, "text/plain")},
    )
    assert upload_res.status_code == 200
    tf_id = upload_res.json()["files"][0]["id"]

    job_res = client.post(
        "/api/meetings/jobs",
        json={"transcriptFileIds": [tf_id], "meetingTitle": "Quick Sync"},
    )
    assert job_res.status_code == 200
    draft = job_res.json()["draft"]
    assert draft is not None

    # Empty lists for everything
    assert len(draft["discussions"]) == 0, f"Expected 0 discussions, got {draft['discussions']}"
    assert len(draft["decisions"]) == 0, f"Expected 0 decisions, got {draft['decisions']}"
    assert len(draft["actionItems"]) == 0, f"Expected 0 action items, got {draft['actionItems']}"
    assert "preliminary greetings" in draft["summary"].lower() or "without substantive" in draft["summary"].lower()


def test_meeting_minutes_draft_editing_and_persistence():
    """Verify that editing draft title, summary, discussions, decisions, actions, and uncertainties succeeds and persists."""
    transcript_text = (
        "Topic: IT Infrastructure.\n"
        "Deepak: We need to upgrade campus Wi-Fi bandwidth.\n"
        "Chair: Decision: Budget of 50,000 rupees approved for network equipment.\n"
        "Deepak: I will contact the vendor by 5 November 2026."
    ).encode("utf-8")

    upload_res = client.post(
        "/api/uploads",
        data={"module": "meeting"},
        files={"files": ("it_meeting.txt", transcript_text, "text/plain")},
    )
    tf_id = upload_res.json()["files"][0]["id"]

    job_res = client.post(
        "/api/meetings/jobs",
        json={"transcriptFileIds": [tf_id], "meetingTitle": "IT Review"},
    )
    job_id = job_res.json()["id"]

    # Modify all fields
    modified_draft = {
        "title": "Edited IT Review 2026",
        "summary": "Custom edited summary of the IT infrastructure upgrade.",
        "discussions": [
            {"topic": "Campus Wi-Fi & Bandwidth Expansion", "points": ["Reviewed existing latency and traffic."], "timestamp": None}
        ],
        "decisions": [
            {"decision": "Budget approved for 50,000 INR with vendor discount.", "status": "agreed", "evidence": "Recorded"}
        ],
        "actionItems": [
            {"task": "Contact vendor for quotation", "owner": "Deepak", "dueDate": "5 November 2026", "uncertain": False}
        ],
        "uncertainties": ["Check if fiber optic line requires civil work permit."]
    }

    update_res = client.put(f"/api/meetings/jobs/{job_id}/draft", json={"draft": modified_draft})
    assert update_res.status_code == 200
    saved_draft = update_res.json()["draft"]

    assert saved_draft["title"] == "Edited IT Review 2026"
    assert saved_draft["summary"] == "Custom edited summary of the IT infrastructure upgrade."
    assert saved_draft["discussions"][0]["topic"] == "Campus Wi-Fi & Bandwidth Expansion"
    assert saved_draft["decisions"][0]["decision"] == "Budget approved for 50,000 INR with vendor discount."
    assert saved_draft["actionItems"][0]["task"] == "Contact vendor for quotation"
    assert saved_draft["uncertainties"] == ["Check if fiber optic line requires civil work permit."]

    # Fetch fresh from GET /api/meetings/jobs/{job_id} to verify database persistence
    get_res = client.get(f"/api/meetings/jobs/{job_id}")
    assert get_res.status_code == 200
    persisted_draft = get_res.json()["draft"]
    assert persisted_draft["title"] == "Edited IT Review 2026"
    assert persisted_draft["summary"] == "Custom edited summary of the IT infrastructure upgrade."


def test_meeting_minutes_title_change_persists_across_reload():
    """Regression test: User changes the title from default 'Institutional Meeting' to a custom title,

    saves draft edits, and reloads the draft from backend/SQLite. Verifies the new title persists
    and does not revert to 'Institutional Meeting'.
    """
    transcript_text = (
        "Chair: We need to review the library renovation before the next semester.\n"
        "Maya: I will book Room 2 by 25 October 2026.\n"
        "Chair: The budget is approved."
    ).encode("utf-8")

    upload_res = client.post(
        "/api/uploads",
        data={"module": "meeting"},
        files={"files": ("transcript.txt", transcript_text, "text/plain")},
    )
    assert upload_res.status_code == 200
    tf_id = upload_res.json()["files"][0]["id"]

    # 1. Job created with default title "Institutional Meeting"
    create_res = client.post(
        "/api/meetings/jobs",
        json={"transcriptFileIds": [tf_id], "meetingTitle": "Institutional Meeting"},
    )
    assert create_res.status_code == 200
    job_id = create_res.json()["id"]
    initial_draft = create_res.json()["draft"]
    assert initial_draft["title"] == "Institutional Meeting"

    # 2. User changes the title to "Board of Trustees Strategic Review 2026"
    new_title = "Board of Trustees Strategic Review 2026"
    updated_draft_payload = dict(initial_draft)
    updated_draft_payload["title"] = new_title

    # 3. User clicks "Save draft edits" -> PUT /api/meetings/jobs/{job_id}/draft
    save_res = client.put(f"/api/meetings/jobs/{job_id}/draft", json={"draft": updated_draft_payload})
    assert save_res.status_code == 200
    assert save_res.json()["draft"]["title"] == new_title

    # 4. User refreshes / reloads via GET /api/meetings/jobs/{job_id}
    reload_res = client.get(f"/api/meetings/jobs/{job_id}")
    assert reload_res.status_code == 200
    reloaded_draft = reload_res.json()["draft"]

    # Verify the new title remains and did NOT revert to "Institutional Meeting"
    assert reloaded_draft["title"] == new_title, \
        f"Expected reloaded title to be '{new_title}', but got '{reloaded_draft['title']}'"
    assert reloaded_draft["title"] != "Institutional Meeting"

    # 5. Also verify GET /api/meetings/jobs/latest returns the newly updated job with the new title
    latest_res = client.get("/api/meetings/jobs/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["id"] == job_id
    assert latest_res.json()["draft"]["title"] == new_title
