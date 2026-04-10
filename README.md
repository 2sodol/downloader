# YouTube Downloader MVP

YouTube 링크를 입력해 로컬에 영상을 다운로드하는 1회성 MVP입니다.

## 스택

- Python 3.10+
- FastAPI
- Uvicorn
- yt-dlp
- ffmpeg
- HTML/CSS/JavaScript
- 메모리 기반 작업 상태 관리

## 사용 방법

의존성 설치:

```bash
cd /Users/wooseok/Desktop/downloader
brew install python@3.12 ffmpeg
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

서버 실행:

```bash
cd /Users/wooseok/Desktop/downloader
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

브라우저에서 접속:

```text
http://127.0.0.1:8000
```

테스트 실행:

```bash
cd /Users/wooseok/Desktop/downloader
source .venv/bin/activate
python -m pytest
```

품질 옵션:

- 호환성 우선 MP4: H.264 + AAC 우선
- 최고화질: YouTube가 제공하는 최고 품질 우선
