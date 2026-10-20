import json
import uuid
import numpy as np
from typing import Optional
from fastapi import HTTPException

from app.services.storage import storage_service
from app.services.extractor import DocumentExtractor
from app.providers.embeddings import get_embedding_provider
from app.providers.llm import get_llm_provider
from app.models.schemas import (
    CollectionResponse,
    QuestionResponse,
    Citation,
)

class RagService:
    def __init__(self):
        self.storage = storage_service

    def create_collection(self, name: str, file_ids: list[str]) -> CollectionResponse:
        collection_id = str(uuid.uuid4())
        
        # Verify files exist in storage
        valid_files = []
        for fid in file_ids:
            record = self.storage.get_file_record(fid)
            if not record:
                raise HTTPException(status_code=404, detail=f"Uploaded file '{fid}' not found.")
            valid_files.append(record)

        # Get active embedding provider early to record metadata
        embedding_provider = get_embedding_provider()

        # Record initial collection state with embedding metadata
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rag_collections (id, name, status, embedding_provider, embedding_dim, embedding_model)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    collection_id,
                    name,
                    "indexing",
                    embedding_provider.provider_name,
                    embedding_provider.dimension,
                    embedding_provider.model_name
                )
            )
            for fid in file_ids:
                cursor.execute(
                    "INSERT INTO rag_collection_files (collection_id, file_id) VALUES (?, ?)",
                    (collection_id, fid)
                )
            conn.commit()

        try:
            chunks_to_insert = []
            chunk_texts = []
            
            for file_rec in valid_files:
                file_path = self.storage.get_file_path(file_rec["id"])
                if not file_path or not file_path.exists():
                    raise RuntimeError(f"File '{file_rec['original_name']}' is missing on disk.")

                passages = DocumentExtractor.extract_from_path(file_path)
                
                # Chunk passages if they are too long (> 800 characters)
                for passage in passages:
                    text = passage.text
                    if len(text) > 800:
                        # Split by sentences or paragraph chunks
                        sub_chunks = [s.strip() for s in text.split("\n") if s.strip()]
                        for sub_idx, sub in enumerate(sub_chunks):
                            chunk_id = str(uuid.uuid4())
                            chunks_to_insert.append({
                                "id": chunk_id,
                                "file_id": file_rec["id"],
                                "file_name": file_rec["original_name"],
                                "page_number": passage.page,
                                "section_title": passage.section,
                                "text": sub,
                            })
                            chunk_texts.append(sub)
                    else:
                        chunk_id = str(uuid.uuid4())
                        chunks_to_insert.append({
                            "id": chunk_id,
                            "file_id": file_rec["id"],
                            "file_name": file_rec["original_name"],
                            "page_number": passage.page,
                            "section_title": passage.section,
                            "text": text,
                        })
                        chunk_texts.append(text)

            if not chunk_texts:
                raise RuntimeError("No readable text could be extracted from the selected documents.")

            # Generate embeddings
            embeddings = embedding_provider.embed_documents(chunk_texts)

            # Store chunks and embeddings in SQLite
            with self.storage._get_connection() as conn:
                cursor = conn.cursor()
                for idx, chunk in enumerate(chunks_to_insert):
                    emb_json = json.dumps(embeddings[idx])
                    cursor.execute(
                        """
                        INSERT INTO rag_chunks (id, collection_id, file_id, chunk_index, page_number, section_title, text, embedding_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            chunk["id"],
                            collection_id,
                            chunk["file_id"],
                            idx,
                            chunk["page_number"],
                            chunk["section_title"],
                            chunk["text"],
                            emb_json
                        )
                    )
                cursor.execute(
                    "UPDATE rag_collections SET status = 'ready' WHERE id = ?",
                    (collection_id,)
                )
                conn.commit()

            return CollectionResponse(
                id=collection_id,
                name=name,
                status="ready",
                fileCount=len(valid_files),
                chunkCount=len(chunks_to_insert),
                embeddingProvider=embedding_provider.provider_name,
                embeddingDim=embedding_provider.dimension
            )

        except Exception as e:
            with self.storage._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE rag_collections SET status = 'failed' WHERE id = ?", (collection_id,))
                conn.commit()
            raise HTTPException(status_code=400, detail=f"Failed to create collection: {str(e)}")

    def get_collection(self, collection_id: str) -> Optional[CollectionResponse]:
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rag_collections WHERE id = ?", (collection_id,))
            col = cursor.fetchone()
            if not col:
                return None
            cursor.execute("SELECT COUNT(DISTINCT file_id) FROM rag_collection_files WHERE collection_id = ?", (collection_id,))
            file_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM rag_chunks WHERE collection_id = ?", (collection_id,))
            chunk_count = cursor.fetchone()[0]

            col_keys = col.keys()
            return CollectionResponse(
                id=col["id"],
                name=col["name"],
                status=col["status"],
                fileCount=file_count,
                chunkCount=chunk_count,
                embeddingProvider=col["embedding_provider"] if "embedding_provider" in col_keys else None,
                embeddingDim=col["embedding_dim"] if "embedding_dim" in col_keys else None
            )

    def answer_question(self, collection_id: str, question: str) -> QuestionResponse:
        col = self.get_collection(collection_id)
        if not col:
            raise HTTPException(status_code=404, detail="Collection not found.")
        if col.status != "ready":
            raise HTTPException(status_code=400, detail=f"Collection is not ready (status: {col.status}).")

        # Retrieve chunks for collection
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT rc.id, rc.file_id, uf.original_name, rc.page_number, rc.section_title, rc.text, rc.embedding_json
                FROM rag_chunks rc
                JOIN uploaded_files uf ON rc.file_id = uf.id
                WHERE rc.collection_id = ?
                """,
                (collection_id,)
            )
            rows = cursor.fetchall()

        if not rows:
            return QuestionResponse(
                answer="No documents or passages were indexed in this collection.",
                citations=[],
                evidenceFound=False
            )

        # Verify embedding model compatibility before calculating similarities
        embedding_provider = get_embedding_provider()
        if col.embeddingDim and embedding_provider.dimension != col.embeddingDim:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Embedding configuration mismatch: Collection '{col.name}' was indexed using "
                    f"'{col.embeddingProvider or 'unknown'}' ({col.embeddingDim}-dimensional vectors), "
                    f"but active provider is '{embedding_provider.provider_name}' ({embedding_provider.dimension}-dimensional vectors). "
                    f"Switch EMBEDDING_PROVIDER back to '{col.embeddingProvider}' or rebuild the collection index."
                )
            )

        # Calculate cosine similarity
        q_emb = np.array(embedding_provider.embed_query(question))

        chunk_data = []
        for row in rows:
            emb = np.array(json.loads(row["embedding_json"]))
            # Cosine similarity between normalized vectors
            sim = float(np.dot(q_emb, emb))
            chunk_data.append((sim, row))

        chunk_data.sort(key=lambda x: x[0], reverse=True)

        # Evidence threshold: if top similarity is virtually zero or no match
        best_sim = chunk_data[0][0]
        if best_sim < 0.08:
            return QuestionResponse(
                answer="No sufficient evidence was found in the private collection to answer this question.",
                citations=[],
                evidenceFound=False,
                providerUsed=embedding_provider.__class__.__name__
            )

        top_chunks = chunk_data[:4]
        
        # Build citations
        citations: list[Citation] = []
        context_parts: list[str] = []
        for sim, row in top_chunks:
            excerpt = row["text"][:220].strip()
            if len(row["text"]) > 220:
                excerpt += "…"
            citations.append(Citation(
                fileId=row["file_id"],
                name=row["original_name"],
                page=row["page_number"],
                section=row["section_title"],
                excerpt=excerpt
            ))
            context_parts.append(f"[{row['original_name']} | Page {row['page_number'] or 'N/A'}]: {row['text']}")

        context_str = "\n\n".join(context_parts)
        prompt = f"Context:\n{context_str}\n\nQuestion: {question}"
        system_instruction = (
            "You are a strict institutional document assistant. Answer the question using ONLY the provided evidence. "
            "Do not guess or assume. If the context does not state the answer, reply that evidence is insufficient."
        )

        llm_provider = get_llm_provider()
        answer = llm_provider.generate(prompt, system_instruction=system_instruction)

        # Check if answer indicates lack of evidence
        is_evidence_found = (
            "not contain sufficient evidence" not in answer.lower()
            and "no direct statement was found" not in answer.lower()
            and "no sufficient evidence" not in answer.lower()
            and "insufficient evidence" not in answer.lower()
        )

        return QuestionResponse(
            answer=answer,
            citations=citations if is_evidence_found else [],
            evidenceFound=is_evidence_found,
            providerUsed=llm_provider.__class__.__name__
        )

rag_service = RagService()
