#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_release.py
========================
Empacota o CineAI em um único arquivo ZIP pronto para distribuição.

Uso:
    python scripts/build_release.py
    python scripts/build_release.py --version 2.1.0 --output ./releases

O ZIP gerado contém:
    cineai-v{version}/
    ├── start.bat          ← duplo clique no Windows
    ├── start.sh           ← ./start.sh no Linux/Mac
    ├── backend/           ← código Python completo
    │   ├── app/
    │   ├── requirements.txt
    │   └── .env.example
    ├── frontend/          ← HTML/CSS/JS
    ├── LEIAME.txt         ← instruções rápidas em texto puro
    └── GUIA_TESTES.md

Arquivos EXCLUÍDOS automaticamente:
    - .env (segredos)
    - .venv/, __pycache__/, *.pyc
    - *.db, *.sqlite3 (banco local)
    - .git/
"""

import argparse
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent.resolve()

INCLUDE_DIRS = ["backend/app", "frontend"]
INCLUDE_FILES = [
    "backend/requirements.txt",
    "backend/.env.example",
    "start.bat",
    "start.sh",
    "GUIA_TESTES.md",
    "LICENSE",
]

EXCLUDE_PATTERNS = {
    # Secrets
    ".env",
    # Caches / compilados
    "__pycache__",
    ".pyc",
    ".pyo",
    ".pyd",
    # Banco de dados
    ".db",
    ".sqlite3",
    # Ambiente virtual
    ".venv",
    "venv",
    "env",
    # IDEs
    ".vscode",
    ".idea",
    # Git
    ".git",
    ".gitignore",
    # Build artifacts
    "dist",
    "build",
    ".egg-info",
    # Sistema
    ".DS_Store",
    "Thumbs.db",
    ".tmp",
}

LEIAME_CONTENT = """\
╔══════════════════════════════════════════════╗
║          CineAI — Início Rápido              ║
╚══════════════════════════════════════════════╝

PRÉ-REQUISITO: Python 3.10 ou superior
  Download: https://www.python.org/downloads/
  IMPORTANTE (Windows): marque "Add Python to PATH"

══════════════════════════════════════════════
 WINDOWS
══════════════════════════════════════════════
  1. Extraia este ZIP em qualquer pasta
  2. Dê duplo clique em: start.bat
  3. Na primeira execução, cole seu token TMDB
  4. O navegador abrirá automaticamente

══════════════════════════════════════════════
 LINUX / macOS
══════════════════════════════════════════════
  1. Extraia o ZIP
  2. Abra o terminal na pasta extraída
  3. chmod +x start.sh && ./start.sh
  4. Cole o token TMDB quando solicitado

══════════════════════════════════════════════
 TOKEN TMDB (gratuito)
══════════════════════════════════════════════
  1. Crie conta em: https://www.themoviedb.org
  2. Acesse: Configurações → API
  3. Copie o "Bearer Token (v4 Auth)"

══════════════════════════════════════════════
 ACESSO
══════════════════════════════════════════════
  Aplicação:  http://localhost:8000
  API Docs:   http://localhost:8000/api/docs

  Guia completo: GUIA_TESTES.md
"""


def should_exclude(path: Path) -> bool:
    for part in path.parts:
        for pat in EXCLUDE_PATTERNS:
            if part == pat or part.endswith(pat):
                return True
    return False


def collect_files(source_dir: Path, relative_to: Path) -> list[tuple[Path, str]]:
    """Return (absolute_path, archive_name) pairs for all non-excluded files."""
    files = []
    for item in source_dir.rglob("*"):
        if item.is_file():
            rel = item.relative_to(relative_to)
            if not should_exclude(rel):
                files.append((item, str(rel)))
    return files


def build_zip(version: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"cineai-v{version}.zip"
    zip_path = output_dir / zip_name
    prefix = f"cineai-v{version}/"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        file_count = 0

        # --- Directories ---
        for rel_dir in INCLUDE_DIRS:
            src_dir = ROOT / rel_dir
            if not src_dir.exists():
                print(f"  [SKIP] Directory not found: {rel_dir}")
                continue
            for abs_path, arc_name in collect_files(src_dir, ROOT):
                zf.write(abs_path, prefix + arc_name)
                file_count += 1
                print(f"  + {arc_name}")

        # --- Individual files ---
        for rel_file in INCLUDE_FILES:
            src = ROOT / rel_file
            if not src.exists():
                print(f"  [SKIP] File not found: {rel_file}")
                continue
            zf.write(src, prefix + rel_file)
            file_count += 1
            print(f"  + {rel_file}")

        # --- LEIAME.txt (generated) ---
        zf.writestr(prefix + "LEIAME.txt", LEIAME_CONTENT)
        file_count += 1
        print(f"  + LEIAME.txt (gerado)")

    size_kb = zip_path.stat().st_size / 1024
    print(f"\n  Total: {file_count} arquivos | {size_kb:.1f} KB")
    return zip_path


def main():
    parser = argparse.ArgumentParser(description="Empacota o CineAI para distribuição")
    parser.add_argument("--version", default=datetime.now().strftime("%Y.%m.%d"), help="Versão do release")
    parser.add_argument("--output", default=str(ROOT / "releases"), help="Pasta de saída")
    args = parser.parse_args()

    print(f"\n  CineAI Release Builder")
    print(f"  ─────────────────────────────────────")
    print(f"  Versão  : {args.version}")
    print(f"  Saída   : {args.output}")
    print(f"  ─────────────────────────────────────\n")

    zip_path = build_zip(args.version, Path(args.output))

    print(f"\n  ✓ Pacote criado: {zip_path}")
    print(f"\n  Para publicar como GitHub Release:")
    print(f"    gh release create v{args.version} {zip_path} --title 'CineAI v{args.version}' --notes 'Release automático'")
    print()


if __name__ == "__main__":
    main()
