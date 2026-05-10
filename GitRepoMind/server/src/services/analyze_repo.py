from __future__ import annotations
import json
import os
from typing import Dict, List, Set


# ── Helpers ──────────────────────────────────────────────────────

def _normalize_path(p: str) -> str:
    """Normalize a path: convert backslashes to forward slashes and strip edges."""
    if not p:
        return ""
    return p.replace("\\", "/").strip().strip("/")


# ── Functionality 1: File Tree Scanner ───────────────────────────────────────

def build_file_tree(paths: List[str]) -> Dict:
    """
    Builds a nested folder structure from a flat list of file paths.

    Returns:
        {
            "total_files": int,
            "folder_structure": { nested dict of folders and files }
        }
    Top-level files are stored under the 'root' key.
    Duplicate paths are silently ignored.
    """
    # Deduplicate
    seen: Set[str] = set()
    unique: List[str] = []
    for p in paths:
        np = _normalize_path(p)
        if np and np not in seen:
            seen.add(np)
            unique.append(np)

    tree: Dict = {}

    def insert(node: Dict, folder_parts: List[str], filename: str):
        if not folder_parts:
            node.setdefault("root", []).append(filename)
            return
        head = folder_parts[0]
        child = node.setdefault(head, {})
        if len(folder_parts) == 1:
            child.setdefault("__files__", []).append(filename)
        else:
            insert(child, folder_parts[1:], filename)

    for p in unique:
        parts = p.split("/")
        if len(parts) == 1:
            insert(tree, [], parts[0])
        else:
            insert(tree, parts[:-1], parts[-1])

    def _clean(node: Dict) -> Dict:
        """Collapse single-child __files__ dicts into plain lists."""
        cleaned: Dict = {}
        for k, v in node.items():
            if k == "__files__":
                cleaned.setdefault("__files__", []).extend(v)
            elif isinstance(v, dict):
                child = _clean(v)
                files = child.get("__files__")
                if files is not None and len(child) == 1:
                    # folder contains only files → store as plain list
                    cleaned[k] = files
                else:
                    if "__files__" in child:
                        loose = child.pop("__files__")
                        child["__files__"] = loose
                    cleaned[k] = child
            else:
                cleaned[k] = v
        return cleaned

    return {
        "total_files": len(unique),
        "folder_structure": _clean(tree),
    }


# ── Functionality 2: Language & Framework Detector ───────────────────────────

# Map file extension → language name
EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".jsx": "JavaScript (React)",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".sh": "Shell",
    ".bat": "Batch",
    ".tf": "Terraform",
    ".sql": "SQL",
}

# Map config/marker filename → framework/tool
FRAMEWORK_SIGNALS: Dict[str, str] = {
    # Python
    "requirements.txt":   "Python (pip)",
    "pyproject.toml":     "Python (pyproject)",
    "setup.py":           "Python (setuptools)",
    "Pipfile":            "Python (pipenv)",
    "manage.py":          "Django",
    "wsgi.py":            "WSGI (Django/Flask)",
    "asgi.py":            "ASGI (Django/FastAPI)",
    # Node / JS
    "package.json":       "Node.js",
    "next.config.js":     "Next.js",
    "next.config.ts":     "Next.js",
    "vite.config.js":     "Vite",
    "vite.config.ts":     "Vite",
    "nuxt.config.js":     "Nuxt.js",
    "angular.json":       "Angular",
    "svelte.config.js":   "SvelteKit",
    # Java
    "pom.xml":            "Maven (Java)",
    "build.gradle":       "Gradle (Java/Kotlin)",
    # Go
    "go.mod":             "Go Modules",
    # Rust
    "Cargo.toml":         "Cargo (Rust)",
    # Infra / DevOps
    "Dockerfile":         "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml":"Docker Compose",
    ".github":            "GitHub Actions",
    "vercel.json":        "Vercel",
    "netlify.toml":       "Netlify",
    "terraform.tf":       "Terraform",
    # DB / config
    "alembic.ini":        "Alembic (DB migrations)",
    ".env":               "Environment Config",
}

def detect_languages_and_frameworks(paths: List[str]) -> Dict:
    """
    Scans file extensions and config filenames to detect:
      - Languages used and their percentage share
      - Frameworks / tools present

    Returns:
        {
            "primary_language": str,
            "languages": { "Python": 60, "JavaScript": 40 },   ← percentages
            "frameworks": ["FastAPI", "Next.js", "Docker"],
            "raw_extension_counts": { ".py": 12, ".js": 5 }
        }
    """
    ext_counts: Dict[str, int] = {}
    frameworks_found: List[str] = []
    frameworks_seen: Set[str] = set()

    for p in paths:
        np = _normalize_path(p)
        if not np:
            continue

        filename = os.path.basename(np)
        _, ext = os.path.splitext(filename)

        # Count language extensions
        if ext and ext in EXTENSION_LANGUAGE_MAP:
            lang = EXTENSION_LANGUAGE_MAP[ext]
            ext_counts[lang] = ext_counts.get(lang, 0) + 1

        # Detect frameworks from filenames
        if filename in FRAMEWORK_SIGNALS:
            fw = FRAMEWORK_SIGNALS[filename]
            if fw not in frameworks_seen:
                frameworks_seen.add(fw)
                frameworks_found.append(fw)

        # Also check the last path component for folder-based signals
        top_folder = np.split("/")[0]
        if top_folder in FRAMEWORK_SIGNALS:
            fw = FRAMEWORK_SIGNALS[top_folder]
            if fw not in frameworks_seen:
                frameworks_seen.add(fw)
                frameworks_found.append(fw)

    total = sum(ext_counts.values()) or 1
    language_percentages = {
        lang: round(count / total * 100, 1)
        for lang, count in sorted(ext_counts.items(), key=lambda x: -x[1])
    }
    primary = max(ext_counts, key=ext_counts.get) if ext_counts else "Unknown"

    return {
        "primary_language": primary,
        "languages": language_percentages,
        "frameworks": frameworks_found,
        "raw_extension_counts": ext_counts,
    }


# ── Functionality 3: Entry Point Identifier ──────────────────────────────────

ENTRY_POINT_SIGNALS: Dict[str, str] = {
    # Python
    "main.py":      "Python main entry",
    "app.py":       "Python app entry (Flask/FastAPI)",
    "server.py":    "Python server entry",
    "run.py":       "Python run script",
    "manage.py":    "Django management entry",
    "wsgi.py":      "WSGI entry",
    "asgi.py":      "ASGI entry",
    # Node / JS / TS
    "index.js":     "Node.js root entry",
    "index.ts":     "TypeScript root entry",
    "server.js":    "Node.js server",
    "server.ts":    "TypeScript server",
    "app.js":       "Node.js app entry",
    "app.ts":       "TypeScript app entry",
    "main.ts":      "TypeScript main entry",
    "main.js":      "JavaScript main entry",
    # Other
    "main.go":      "Go main entry",
    "Main.java":    "Java main class",
    "main.rs":      "Rust main entry",
    "index.html":   "HTML entry (frontend)",
    "Makefile":     "Build entry (make)",
    "Procfile":     "Heroku process entry",
}

def identify_entry_points(paths: List[str]) -> List[Dict]:
    """
    Scans paths for known entry-point filenames.

    Returns a list of dicts:
        [
            { "file": "src/app.py", "type": "Python app entry (Flask/FastAPI)" },
            ...
        ]
    """
    found: List[Dict] = []
    seen_types: Set[str] = set()

    for p in paths:
        np = _normalize_path(p)
        filename = os.path.basename(np)
        if filename in ENTRY_POINT_SIGNALS:
            entry_type = ENTRY_POINT_SIGNALS[filename]
            if entry_type not in seen_types:
                seen_types.add(entry_type)
                found.append({"file": np, "type": entry_type})

    return found


# ── Functionality 4: Dependency Extractor ────────────────────────────────────

DEPENDENCY_FILES: List[str] = [
    "requirements.txt",
    "package.json",
    "Pipfile",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Gemfile",
]

def extract_dependency_files(paths: List[str]) -> Dict:
    """
    Detects which dependency/manifest files exist in the repo.

    Returns:
        {
            "found": ["requirements.txt", "package.json"],
            "missing": ["go.mod", "Cargo.toml", ...]
        }
    """
    filenames_in_repo = {os.path.basename(_normalize_path(p)) for p in paths}
    found = [df for df in DEPENDENCY_FILES if df in filenames_in_repo]
    missing = [df for df in DEPENDENCY_FILES if df not in filenames_in_repo]
    return {"found": found, "missing": missing}


# ── Functionality 5: Architecture Pattern Detector ───────────────────────────

ARCH_FOLDER_SIGNALS: Dict[str, str] = {
    "models":      "Data Layer (Models)",
    "views":       "Presentation Layer (Views/MVC)",
    "controllers": "Controller Layer (MVC)",
    "routes":      "Routing Layer (REST API)",
    "api":         "API Layer",
    "services":    "Service Layer",
    "middleware":  "Middleware Layer",
    "components":  "Frontend Components",
    "pages":       "Frontend Pages (Next.js/Nuxt)",
    "hooks":       "React Hooks",
    "store":       "State Management",
    "agents":      "LLM Agents",
    "chains":      "LangChain Chains",
    "prompts":     "LLM Prompts",
    "embeddings":  "Vector Embeddings",
    "db":          "Database Layer",
    "migrations":  "DB Migrations",
    "tests":       "Test Suite",
    "test":        "Test Suite",
    "infra":       "Infrastructure",
    "deploy":      "Deployment Config",
    "docker":      "Docker Config",
}

def detect_architecture(paths: List[str]) -> Dict:
    """
    Infers architecture patterns from the presence of specific folders.

    Returns:
        {
            "detected_layers": ["API Layer", "Service Layer", ...],
            "project_type": "Full Stack RAG Application",
            "matched_folders": { "api": "src/api", ... }
        }
    """
    top_folders: Set[str] = set()
    for p in paths:
        np = _normalize_path(p)
        parts = np.split("/")
        # Collect every folder name at every depth
        for part in parts[:-1]:
            top_folders.add(part.lower())

    detected_layers: List[str] = []
    matched_folders: Dict[str, str] = {}

    for folder, layer in ARCH_FOLDER_SIGNALS.items():
        if folder.lower() in top_folders and layer not in detected_layers:
            detected_layers.append(layer)
            matched_folders[folder] = layer

    # Infer project type from combination of layers
    layers_set = set(detected_layers)
    has_frontend  = any("Frontend" in l or "Pages" in l or "Component" in l for l in layers_set)
    has_backend   = any("API" in l or "Service" in l or "Route" in l for l in layers_set)
    has_llm       = any("LLM" in l or "Agent" in l or "Chain" in l or "Embedding" in l for l in layers_set)
    has_db        = any("Database" in l or "Migration" in l for l in layers_set)

    if has_llm and has_frontend and has_backend:
        project_type = "Full Stack RAG / LLM Application"
    elif has_llm and has_backend:
        project_type = "LLM Backend / RAG API"
    elif has_frontend and has_backend and has_db:
        project_type = "Full Stack Web Application (MVC/Service)"
    elif has_frontend and has_backend:
        project_type = "Full Stack Web Application"
    elif has_backend:
        project_type = "Backend API / Microservice"
    elif has_frontend:
        project_type = "Frontend Application"
    else:
        project_type = "Script / Library / Utility"

    return {
        "project_type": project_type,
        "detected_layers": detected_layers,
        "matched_folders": matched_folders,
    }


# ── Functionality 6: Folder Pattern Classifier ───────────────────────────────

KNOWN_PATTERNS: List[str] = [
    "src", "tests", "test", "api", "models", "components",
    "hooks", "utils", "lib", "assets", "public", "config",
    "db", "controllers", "services", "middleware", "pages",
    "store", "agents", "chains", "prompts", "infra", "deploy",
]

def classify_folder_patterns(folder_structure: Dict) -> Dict:
    """
    Detects which well-known folder patterns exist in the tree.

    Returns:
        {
            "patterns_detected": ["src", "tests", "api"],
            "matches": { "src": "src", "tests": "tests/unit" }
        }
    """
    detected: List[str] = []
    matches: Dict[str, str] = {}

    def traverse(node: Dict, prefix: str = ""):
        for name, child in node.items():
            if name == "__files__":
                continue
            path = f"{prefix}/{name}" if prefix else name
            if name in KNOWN_PATTERNS and name not in matches:
                detected.append(name)
                matches[name] = path
            if isinstance(child, dict):
                traverse(child, path)

    traverse(folder_structure)
    return {"patterns_detected": detected, "matches": matches}


# ── Functionality 7: File Type Stats ─────────────────────────────────────────

def file_type_stats(paths: List[str]) -> Dict[str, int]:
    """
    Counts files grouped by extension.
    Files without an extension are counted under 'no_extension'.
    """
    counts: Dict[str, int] = {}
    seen: Set[str] = set()
    for p in paths:
        np = _normalize_path(p)
        if not np or np in seen:
            continue
        seen.add(np)
        _, ext = os.path.splitext(os.path.basename(np))
        key = ext if ext else "no_extension"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


# ── Report Generator ──────────────────────────────────────────────────────────

def generate_readme_overview(result: Dict) -> str:
    """
    Generates a human-readable README-style overview from the analysis result.
    """
    lang_info   = result.get("language_info", {})
    entry_pts   = result.get("entry_points", [])
    arch        = result.get("architecture", {})
    deps        = result.get("dependency_files", {})
    file_types  = result.get("file_types", {})

    primary_lang = lang_info.get("primary_language", "Unknown")
    frameworks   = ", ".join(lang_info.get("frameworks", [])) or "None detected"
    project_type = arch.get("project_type", "Unknown")
    layers       = "\n".join(f"  - {l}" for l in arch.get("detected_layers", [])) or "  - None detected"

    entry_list = "\n".join(
        f"  - `{e['file']}` — {e['type']}" for e in entry_pts
    ) or "  - None detected"

    dep_found = ", ".join(deps.get("found", [])) or "None"

    top_types = list(file_types.items())[:5]
    type_summary = ", ".join(f"{ext}({count})" for ext, count in top_types)

    overview = f"""
## 📁 Repository Analysis

**Project Type:**     {project_type}
**Primary Language:** {primary_lang}
**Frameworks/Tools:** {frameworks}
**Total Files:**      {result.get("total_files", 0)}

### 🚀 Entry Points
{entry_list}

### 🏗️ Detected Architecture Layers
{layers}

### 📦 Dependency Files Found
{dep_found}

### 📊 Top File Types
{type_summary}
""".strip()
    return overview


def to_json(summary: Dict) -> str:
    """Return a pretty-printed JSON string for any summary dict."""
    return json.dumps(summary, indent=2, sort_keys=False)


# ── Master Analyzer ───────────────────────────────────────────────────────────

def analyze_repository(paths: List[str]) -> Dict:
    """
    High-level wrapper: runs all 6 analysis steps and returns a unified report.

    Args:
        paths: flat list of file path strings (e.g. from GitHubService.get_all_files)

    Returns:
        Unified analysis dict with keys:
            total_files, folder_structure, file_types, patterns,
            language_info, entry_points, dependency_files,
            architecture, readme_overview
    """
    # 1. File tree
    tree_summary  = build_file_tree(paths)
    folder_struct = tree_summary.get("folder_structure", {})

    # 2. Language & framework detection
    lang_info = detect_languages_and_frameworks(paths)

    # 3. Entry points
    entry_points = identify_entry_points(paths)

    # 4. Dependency files
    dep_files = extract_dependency_files(paths)

    # 5. Architecture
    architecture = detect_architecture(paths)

    # 6. File type stats & folder patterns
    file_types = file_type_stats(paths)
    patterns   = classify_folder_patterns(folder_struct)

    result = {
        "total_files":      tree_summary.get("total_files", 0),
        "folder_structure": folder_struct,
        "file_types":       file_types,
        "patterns":         patterns,
        "language_info":    lang_info,
        "entry_points":     entry_points,
        "dependency_files": dep_files,
        "architecture":     architecture,
    }

    # 7. Auto-generate README overview
    result["readme_overview"] = generate_readme_overview(result)

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Standalone test: pass a GitHub repo URL and analyze it
    from github_service import GitHubService

    svc = GitHubService()
    repo_url = input("Enter GitHub repository URL: ").strip()
    branch   = input("Enter branch (default: main): ").strip() or "main"

    svc.get_repo_info(repo_url)
    raw_files = svc.get_all_files(branch)

    if not raw_files:
        print("No files found.")
    else:
        paths = [f["path"] for f in raw_files if f.get("path")]
        result = analyze_repository(paths)

        print("\n" + "=" * 60)
        print("        STATIC ANALYSIS REPORT")
        print("=" * 60)
        print(to_json(result))

        print("\n" + "=" * 60)
        print("        README OVERVIEW")
        print("=" * 60)
        print(result["readme_overview"])        