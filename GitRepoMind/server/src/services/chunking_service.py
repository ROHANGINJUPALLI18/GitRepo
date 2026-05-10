"""
Text Chunking Service

Splits large files into overlapping chunks for embedding.
Chunk sizes are optimized by file type to respect token limits (~8000 tokens).
Metadata (path, line numbers, chunk index) is included for provenance.
"""

import re
from typing import Dict, List, Optional


# ── Token Estimation ─────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """
    Rough estimate of tokens from text.
    Simple heuristic: 1 token ≈ 4 characters (common for English text).
    Later replace with `tiktoken` for model-accurate counts.
    """
    return max(1, len(text) // 4)


# ── File Type Detection ──────────────────────────────────────────────────────

def _detect_file_type(file_path: str) -> str:
    """
    Detect file type from extension or name.
    Returns one of: 'code', 'markdown', 'config', 'unknown'
    """
    path_lower = file_path.lower()

    # Code files: Python, JavaScript, TypeScript, Java, Go, Rust, C++
    code_exts = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.cs'}
    if any(path_lower.endswith(ext) for ext in code_exts):
        return 'code'

    # Markdown / docs
    doc_exts = {'.md', '.markdown', '.txt', '.rst'}
    doc_names = {'readme', 'changelog', 'contributing', 'license', 'install'}
    if any(path_lower.endswith(ext) for ext in doc_exts) or \
       any(doc_name in path_lower for doc_name in doc_names):
        return 'markdown'

    # Config files: JSON, YAML, TOML
    config_exts = {'.json', '.yaml', '.yml', '.toml', '.ini', '.conf', '.config'}
    config_names = {'config', 'settings', '.env', 'dockerfile', 'makefile'}
    if any(path_lower.endswith(ext) for ext in config_exts) or \
       any(config_name in path_lower for config_name in config_names):
        return 'config'

    return 'unknown'


# ── Chunk Size Configuration ─────────────────────────────────────────────────

CHUNK_CONFIG: Dict[str, Dict[str, int]] = {
    'code':     {'size': 500, 'overlap': 50},
    'markdown': {'size': 300, 'overlap': 30},
    'config':   {'size': 200, 'overlap': 20},
    'unknown':  {'size': 500, 'overlap': 50},  # fallback to code defaults
}


# ── Smart Text Splitting ─────────────────────────────────────────────────────

def _split_by_boundaries(text: str, file_type: str) -> List[str]:
    """
    Split text on sensible boundaries to avoid breaking code/logic.
    For code: prefer blank lines (logical block boundaries).
    For markdown: prefer double newlines or heading lines.
    Falls back to newline splits, then character-based split if needed.
    """
    if file_type == 'code':
        # Try splitting on blank lines first (logical blocks in code)
        parts = re.split(r'\n\s*\n+', text)
        if len(parts) > 1:
            return parts
        # Fall back to newline splits
        return text.split('\n')

    elif file_type == 'markdown':
        # Try splitting on headings or double newlines
        parts = re.split(r'\n\n+|\n(?=#+\s)', text)
        if len(parts) > 1:
            return parts
        # Fall back to newline splits
        return text.split('\n')

    else:  # config, unknown
        # For config/JSON, split on top-level structures or blank lines
        parts = re.split(r'\n\s*\n+', text)
        if len(parts) > 1:
            return parts
        return text.split('\n')


def _build_chunks_with_overlap(
    text: str,
    chunk_size: int,
    overlap: int,
    file_type: str
) -> List[str]:
    """
    Build chunks with overlap by token count.
    First tries splitting by boundaries; if a single boundary is too large,
    falls back to character-based splitting.
    """
    # Split by logical boundaries first
    boundaries = _split_by_boundaries(text, file_type)

    chunks = []
    current_chunk = ""
    current_tokens = 0
    overlap_text = ""

    for boundary in boundaries:
        boundary_tokens = estimate_tokens(boundary)

        # If a single boundary exceeds chunk_size, split it further
        if boundary_tokens > chunk_size:
            # Fall back to character-based split for this large boundary
            char_chunk_size = int(chunk_size * 4)  # Rough conversion: tokens*4 ≈ chars
            for i in range(0, len(boundary), char_chunk_size):
                fragment = boundary[i:i + char_chunk_size]
                fragment_tokens = estimate_tokens(fragment)

                if current_tokens + fragment_tokens > chunk_size and current_chunk:
                    # Save current chunk and start new one with overlap
                    chunks.append(current_chunk)
                    # Keep overlap_text from end of current chunk
                    overlap_tokens = estimate_tokens(overlap_text)
                    while overlap_tokens > overlap and overlap_text:
                        lines = overlap_text.split('\n')
                        overlap_text = '\n'.join(lines[1:]) if len(lines) > 1 else ""
                        overlap_tokens = estimate_tokens(overlap_text)
                    current_chunk = overlap_text + fragment
                    current_tokens = overlap_tokens + fragment_tokens
                else:
                    current_chunk += fragment
                    current_tokens += fragment_tokens

                # Track overlap from the end of the fragment
                overlap_text = fragment[-min(500, len(fragment)):]  # Last 500 chars as overlap seed

        else:
            # Boundary fits or nearly fits in current chunk
            if current_tokens + boundary_tokens > chunk_size and current_chunk:
                # Save current chunk with overlap
                chunks.append(current_chunk)
                # Overlap: take last few boundaries to maintain context
                lines = current_chunk.split('\n')
                overlap_text = '\n'.join(lines[-min(5, len(lines)):])
                overlap_tokens = estimate_tokens(overlap_text)
                if overlap_tokens > overlap:
                    # Trim overlap if too large
                    overlap_text = overlap_text[-(overlap * 4):]
                current_chunk = overlap_text + "\n" + boundary if overlap_text else boundary
                current_tokens = estimate_tokens(current_chunk)
            else:
                current_chunk += "\n" + boundary if current_chunk else boundary
                current_tokens += boundary_tokens

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk)

    return [c.strip() for c in chunks if c.strip()]


# ── Line Number Tracking ─────────────────────────────────────────────────────

def _estimate_line_ranges(text: str, chunks: List[str]) -> List[tuple]:
    """
    Estimate start and end line numbers for each chunk.
    This is an approximation based on newline positions.
    """
    text_lines = text.split('\n')
    cumulative_lines = {0: 0}
    for i, chunk in enumerate(chunks):
        if i == 0:
            cumulative_lines[i + 1] = chunk.count('\n') + 1
        else:
            cumulative_lines[i + 1] = cumulative_lines[i] + chunk.count('\n') + 1

    line_ranges = []
    for i in range(len(chunks)):
        start_line = cumulative_lines.get(i, 0) + 1
        end_line = cumulative_lines.get(i + 1, len(text_lines))
        line_ranges.append((start_line, end_line))

    return line_ranges


# ── Main Chunker API ────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    file_path: str = "",
    file_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
) -> List[Dict]:
    """
    Chunk text into overlapping pieces, optimized by file type.

    Args:
        text: The full file content.
        file_path: Original file path (used for metadata and type detection).
        file_type: Explicit type ('code', 'markdown', 'config'). Auto-detected if None.
        chunk_size: Max token count per chunk. Uses type-specific default if None.
        overlap: Max token count of overlap between chunks. Uses type-specific default if None.

    Returns:
        List of chunk dicts with keys:
            - 'text': chunk content
            - 'chunk_index': 0-based index
            - 'start_line': estimated line number (1-based)
            - 'end_line': estimated line number (1-based)
            - 'path': original file path
            - 'tokens': estimated token count
    """
    if not text or not text.strip():
        return []

    # Auto-detect file type if not provided
    if file_type is None:
        file_type = _detect_file_type(file_path)

    # Use type-specific defaults if not provided
    config = CHUNK_CONFIG.get(file_type, CHUNK_CONFIG['unknown'])
    if chunk_size is None:
        chunk_size = config['size']
    if overlap is None:
        overlap = config['overlap']

    # For very small files, return as single chunk
    text_tokens = estimate_tokens(text)
    if text_tokens <= chunk_size:
        lines = text.count('\n') + 1
        return [
            {
                'text': text,
                'chunk_index': 0,
                'start_line': 1,
                'end_line': lines,
                'path': file_path,
                'tokens': text_tokens,
            }
        ]

    # Build chunks with overlap
    chunks = _build_chunks_with_overlap(text, chunk_size, overlap, file_type)
    line_ranges = _estimate_line_ranges(text, chunks)

    # Create chunk dicts with metadata
    result = []
    for idx, chunk_text in enumerate(chunks):
        chunk_tokens = estimate_tokens(chunk_text)
        start_line, end_line = line_ranges[idx] if idx < len(line_ranges) else (1, 1)
        result.append(
            {
                'text': chunk_text,
                'chunk_index': idx,
                'start_line': start_line,
                'end_line': end_line,
                'path': file_path,
                'tokens': chunk_tokens,
            }
        )

    return result


# ── Summary Stats ────────────────────────────────────────────────────────────

def get_chunking_summary(chunks: List[Dict]) -> Dict:
    """Return summary stats about a set of chunks."""
    total_tokens = sum(c.get('tokens', 0) for c in chunks)
    return {
        'total_chunks': len(chunks),
        'total_tokens': total_tokens,
        'avg_tokens_per_chunk': total_tokens // len(chunks) if chunks else 0,
    }


# ── Entry point (for testing) ────────────────────────────────────────────────

if __name__ == "__main__":
    # Quick test
    sample_code = """
def login(username, password):
    '''Authenticate user.'''
    user = db.find_user(username)
    if not user:
        return {'error': 'User not found'}
    
    if verify_password(password, user.password_hash):
        return {'token': generate_token(user.id)}
    return {'error': 'Invalid credentials'}


def logout(token):
    '''Invalidate token.'''
    cache.delete(token)
    return {'status': 'logged out'}
""" * 20  # Repeat to make it larger

    chunks = chunk_text(sample_code, "auth.py", file_type="code")
    print(f"Chunks created: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i}: {chunk['tokens']} tokens, lines {chunk['start_line']}-{chunk['end_line']}")
