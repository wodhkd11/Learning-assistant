#!/usr/bin/env python3
"""KALF 초기화 스크립트.

다른 PC에서 처음 실행할 때 필요한 모든 환경을 자동으로 구성한다.
사용법: python scripts/setup.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, **kwargs)


def step1_install_packages() -> None:
    print("\n[Step 1] Python 패키지 설치 중...")
    req = PROJECT_DIR / "requirements.txt"
    result = _run([sys.executable, "-m", "pip", "install", "-r", str(req)])
    if result.returncode != 0:
        print("  오류: pip install 실패. requirements.txt를 확인하세요.")
        sys.exit(1)
    print("  완료.")


def step2_check_ollama() -> None:
    print("\n[Step 2] Ollama 설치 확인...")
    try:
        result = _run(["ollama", "--version"], capture_output=True)
        ok = result.returncode == 0
    except FileNotFoundError:
        ok = False
    if not ok:
        print("  Ollama가 설치되지 않았습니다.")
        print("  https://ollama.com/download 에서 설치 후 다시 실행하세요.")
        sys.exit(1)
    version = result.stdout.decode(errors="replace").strip()
    print(f"  설치됨: {version}")


def step3_check_models() -> None:
    print("\n[Step 3] Ollama 모델 확인 및 다운로드...")
    try:
        result = _run(["ollama", "list"], capture_output=True, text=True)
        installed = result.stdout if result.returncode == 0 else ""
    except FileNotFoundError:
        installed = ""

    if "llama3:8b" not in installed:
        print("  llama3:8b 없음 → 자동 다운로드 중... (수 분 소요)")
        _run(["ollama", "pull", "llama3:8b"])
    else:
        print("  llama3:8b 이미 설치됨.")

    if "phi3:mini" not in installed:
        ans = input("  (선택) phi3:mini 도 설치하시겠습니까? [y/N] ").strip().lower()
        if ans == "y":
            print("  phi3:mini 다운로드 중...")
            _run(["ollama", "pull", "phi3:mini"])
        else:
            print("  phi3:mini 건너뜀.")
    else:
        print("  phi3:mini 이미 설치됨.")


def step4_create_env() -> None:
    print("\n[Step 4] .env 파일 확인...")
    env_path = PROJECT_DIR / ".env"
    example_path = PROJECT_DIR / ".env.example"

    if env_path.exists():
        print("  .env 이미 존재함 — 스킵.")
        return

    if not example_path.exists():
        print("  경고: .env.example 없음. .env 생성을 건너뜁니다.")
        return

    shutil.copy(example_path, env_path)
    print("  .env.example → .env 복사 완료.")
    print("  필수 항목을 .env에 입력하세요:")
    print("    ANTHROPIC_API_KEY, XAI_API_KEY, GEMINI_API_KEY, GROQ_API_KEY")


def step5_create_dirs() -> None:
    print("\n[Step 5] 필수 디렉토리 생성...")
    dirs = [
        PROJECT_DIR / "obsidian_vault",
        PROJECT_DIR / ".temp",
        PROJECT_DIR / "data" / "chroma",
    ]
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True)
            print(f"  생성: {d.relative_to(PROJECT_DIR)}")
        else:
            print(f"  존재: {d.relative_to(PROJECT_DIR)}")


def step6_check_chroma() -> None:
    print("\n[Step 6] ChromaDB 초기화 확인...")
    chroma_dir = PROJECT_DIR / "data" / "chroma"
    files = list(chroma_dir.iterdir()) if chroma_dir.exists() else []
    if not files:
        print("  data/chroma/ 가 비어있습니다.")
        print("  기존 볼트 파일이 있다면 아래 명령으로 색인하세요:")
        print("    python scripts/index_vault.py")
    else:
        print("  ChromaDB 데이터 존재함.")


def step7_done() -> None:
    print("\n" + "=" * 50)
    print("  KALF 초기화 완료.")
    print("=" * 50)
    print("  FastAPI 서버 시작:")
    print("    uvicorn backend.main:app --reload")
    print("  또는 트레이 앱 실행:")
    print("    dist\\KALF.exe")
    print("=" * 50)


if __name__ == "__main__":
    print("KALF 초기화 스크립트 시작")
    step1_install_packages()
    step2_check_ollama()
    step3_check_models()
    step4_create_env()
    step5_create_dirs()
    step6_check_chroma()
    step7_done()
