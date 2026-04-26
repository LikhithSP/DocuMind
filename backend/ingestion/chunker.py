"""Recursive character/token text chunker.
TICKET-103:
- Configurable chunk size (default ~512 tokens / ~1500 chars) and overlap (~50 tokens / ~150 chars).
- Preserves paragraph/sentence breaks over arbitrary cuts.
- Retains document_id, source_page, chunk_index in metadata.
"""
from typing import List, Dict, Any
import re
from backend.ingestion.extractor import ExtractedPage

class Chunk:
    def __init__(
        self, 
        chunk_id: str, 
        document_id: str, 
        text: str, 
        source_page: int, 
        chunk_index: int,
        token_count: int
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.text = text
        self.source_page = source_page
        self.chunk_index = chunk_index
        self.token_count = token_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "source_page": self.source_page,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count
        }

class RecursiveChunker:
    def __init__(
        self,
        chunk_size_chars: int = 1500, # Approx 500-512 tokens
        chunk_overlap_chars: int = 200, # Approx 50-70 tokens
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size_chars
        self.chunk_overlap = chunk_overlap_chars
        # Hierarchical separators preferring paragraphs -> sentences -> clauses -> words
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 3)

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursively splits text using the hierarchy of separators."""
        final_chunks: List[str] = []
        if not text.strip():
            return []
        
        # Choose separator
        separator = ""
        new_separators = []
        for i, s in enumerate(separators):
            if s in text:
                separator = s
                new_separators = separators[i + 1:]
                break
        
        if not separator:
            # No matching separator found, perform character slicing with overlap
            return [text[i:i + self.chunk_size] for i in range(0, len(text), max(1, self.chunk_size - self.chunk_overlap))]
        
        splits = text.split(separator)
        good_splits: List[str] = []
        
        for s in splits:
            if not s.strip():
                continue
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if new_separators:
                    other_splits = self._split_text(s, new_separators)
                    good_splits.extend(other_splits)
                else:
                    # Slice hard
                    good_splits.extend([s[i:i + self.chunk_size] for i in range(0, len(s), max(1, self.chunk_size - self.chunk_overlap))])
        
        # Merge splits up to chunk_size with chunk_overlap
        current_chunk = ""
        for piece in good_splits:
            if not current_chunk:
                current_chunk = piece
            elif len(current_chunk) + len(separator) + len(piece) <= self.chunk_size:
                current_chunk += separator + piece
            else:
                final_chunks.append(current_chunk.strip())
                # Overlap: keep tail of current_chunk
                if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                    overlap_seed = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_seed + " " + piece
                else:
                    current_chunk = piece
        
        if current_chunk.strip():
            final_chunks.append(current_chunk.strip())
            
        return final_chunks

    def chunk_document(self, document_id: str, pages: List[ExtractedPage]) -> List[Chunk]:
        """Splits extracted document pages into structured overlapping chunks."""
        chunks: List[Chunk] = []
        chunk_idx = 0
        
        for page in pages:
            page_text = page.text.strip()
            if not page_text:
                continue
            
            splits = self._split_text(page_text, self.separators)
            for split in splits:
                if len(split.strip()) < 10:
                    continue # Skip trivial noise
                
                chunk_id = f"{document_id}_c{chunk_idx}"
                token_count = self._estimate_tokens(split)
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text=split.strip(),
                    source_page=page.page_number,
                    chunk_index=chunk_idx,
                    token_count=token_count
                ))
                chunk_idx += 1
                
        return chunks
