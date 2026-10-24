# GitHub 비공개 저장소 업로드와 EXE 배포

이 폴더는 `main` 브랜치로 초기화되어 있습니다. 소스와 문서는 스테이징되어 있으며 첫 커밋과 원격 저장소 연결은 사용자가 진행합니다.

## 1. 소스 업로드

GitHub에서 **Private** 빈 저장소 `RegionCompositor`를 만드세요. GitHub 쪽 README 자동 생성은 끄세요. 프로젝트 폴더에서 아래 명령의 이름·이메일·계정 값을 본인 것으로 바꿔 실행합니다.

```powershell
git config user.name "YOUR_NAME"
git config user.email "YOUR_GIT_EMAIL"
git add .
git diff --cached --stat
git commit -m "Add bilingual RegionCompositor desktop app"
git remote add origin https://github.com/YOUR_ACCOUNT/RegionCompositor.git
git push -u origin main
```

이미 `origin`이 있으면 `git remote -v`로 주소를 확인하세요. 업로드 인증은 사용 중인 Git 클라이언트에서 진행합니다.

## 2. EXE 배포

저장소의 **Releases → Draft a new release**에서 `main`을 대상으로 새 태그(예: `v0.1.0`)를 지정하세요. 릴리스 설명에는 [RELEASE_NOTES.md](RELEASE_NOTES.md) 내용을 사용하고, 로컬 `release/` 폴더의 다음 파일을 첨부하세요.

- `RegionCompositor-windows-x64.zip`: 실행 파일과 사용 안내
- `SHA256SUMS.txt`: EXE와 ZIP 무결성 확인용 해시

내용을 확인한 뒤 릴리스를 게시하세요. 비공개 저장소의 릴리스 접근 권한은 저장소 접근 권한을 따릅니다. 공식 절차: [GitHub 릴리스 관리](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

EXE, ZIP, `.venv`, `build`, `dist`, `release`는 Git에서 제외됩니다. 소스 ZIP을 웹으로 올릴 경우 먼저 압축을 풀고 내부 파일을 올려야 코드와 README가 표시됩니다.

## 3. 다시 빌드하기

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

`build.ps1`은 테스트 통과 후 `dist/RegionCompositor.exe`를 만듭니다. 배포 ZIP은 현재 검증한 빌드의 스냅샷이므로 재빌드 후 EXE와 해시도 함께 갱신하세요.
