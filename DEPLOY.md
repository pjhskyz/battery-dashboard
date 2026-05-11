# 🚀 배포 가이드 — 30분에 운영 시작

이 문서는 빠른 운영 셋업만 다룹니다. 자세한 설명은 [README.md](README.md) 참고.

```
선행 조건: GitHub 계정만 있으면 됩니다.
           (gh CLI나 Vercel 계정 불필요)
```

---

## ✅ 6단계 체크리스트

### Step 1 — Git 저장소 초기화 (2분)

압축 푼 폴더(`battery-dashboard/`)에서 터미널 열고:

```bash
cd ~/Downloads/battery-dashboard   # 압축 푼 위치에 맞게 조정
git init
git branch -M main
git add .
git commit -m "initial: battery materials dashboard"
```

> ⚠️ Git 처음 쓰시면: `git config --global user.email "your@email.com"` 와 `git config --global user.name "Your Name"` 먼저 실행

### Step 2 — GitHub 레포 만들기 (2분)

1. 브라우저에서 **https://github.com/new** 접속
2. Repository name: `battery-dashboard`
3. **Public** 또는 **Private** (Public이면 GitHub Pages 무료, Private이면 유료 플랜 필요)
4. **"Add a README file" 체크 해제** ⚠️ (기존 코드와 충돌 방지)
5. **Create repository** 클릭

### Step 3 — 코드 푸시 (1분)

GitHub이 알려준 명령어를 그대로 실행 (USERNAME은 본인 계정명):

```bash
git remote add origin https://github.com/USERNAME/battery-dashboard.git
git push -u origin main
```

> ⚠️ 처음 push하면 인증 요청. 비밀번호 대신 **Personal Access Token** 필요:
> github.com → Settings(우상단 프로필) → Developer settings → Personal access tokens
> → Tokens (classic) → Generate new token → `repo` 권한만 체크 → 생성 → 복사해서 비밀번호 자리에 붙여넣기

### Step 4 — Actions 권한 설정 (30초)

레포 페이지에서:

1. **Settings** 탭 (레포 메뉴 맨 오른쪽)
2. 왼쪽 사이드바 **Actions → General**
3. 맨 아래 **Workflow permissions** 섹션
4. **"Read and write permissions"** 라디오 버튼 선택
5. **Save** 클릭

> 이게 있어야 GitHub Actions가 매일 `data/current.json`을 자동 commit 가능

### Step 5 — 첫 데이터 수집 실행 (2분)

1. 레포의 **Actions** 탭으로 이동
2. 왼쪽에서 **"Update battery prices"** 워크플로우 클릭
3. 오른쪽의 **"Run workflow"** 드롭다운 → **Run workflow** 버튼
4. ~1분 기다리면 ✅ 녹색 체크 표시
5. **Code** 탭으로 가서 `data/current.json` 클릭 → 최근 commit 시간이 방금 전인지 확인

> ❌ 빨간 X가 뜨면? 워크플로우 클릭 → 로그 확인. 보통 Sina Finance 차단 (GitHub은 미국 IP라 보통 안 막힘) 또는 SMM 응답 형식 변경. 4개 중 2개 이상 성공하면 일단 OK.

### Step 6 — GitHub Pages로 호스팅 (2분)

1. **Settings → Pages** (왼쪽 사이드바)
2. **Source: Deploy from a branch** 선택
3. **Branch: main**, **Folder: / (root)** 선택
4. **Save** 클릭
5. ~1분 기다린 후 페이지 새로고침 → 상단에 **"Your site is live at https://USERNAME.github.io/battery-dashboard/"** 표시

**그 URL이 대시보드입니다.** 모바일에서도 그대로 접속 가능.

---

## 🟢 정상 운영 확인

대시보드 URL 접속 → 상단 배너 확인:
- 🟢 **라이브** 라벨 → 데이터가 GitHub에서 fetch 됨 (정상)
- 📦 **임베디드** 라벨 → fetch 실패, 인라인 샘플 사용 (Step 5/6 다시 확인)

스크롤하면서 6개 카드의 변동률·차트 모양이 합리적인지 확인 (스크린샷과 약간 다를 수 있음 — 이제 진짜 데이터니까).

---

## 📅 자동 갱신 주기

`.github/workflows/update.yml`에 정의되어 있습니다:
- **평일 KST 18:00** (UTC 09:00) — Sina/SHFE 일일정산 후
- **주말 KST 09:00** — 한 번 더

수동으로도 가능: Actions 탭 → Run workflow

---

## 🎨 자주 하실 만한 커스터마이징

| 하고 싶은 것 | 어디서 |
|---|---|
| 종목 추가 (예: 코발트, 망간) | `scraper/main.py`의 `COMMODITIES` 리스트 + `scraper/fetch_yahoo.py` 같은 파일에 함수 추가 |
| 갱신 주기 변경 | `.github/workflows/update.yml`의 `cron:` 라인 |
| 카드 색상·레이아웃 | `index.html`의 `buildCard()` 함수 |
| 모바일 가로 1열 | 기본값 그대로 (Tailwind 반응형 그리드) |
| Slack/텔레그램 알림 추가 | `scraper/main.py` 끝에 임계치 체크 + webhook 호출 추가 |

---

## ❓ 트러블슈팅

| 증상 | 진단 |
|---|---|
| 대시보드가 임베디드 모드 | data/current.json 파일이 없거나 GitHub Actions 미실행 → Step 5 다시 |
| Actions가 commit 못함 | Workflow permissions 확인 → Step 4 |
| Sina Finance 403/타임아웃 | 일시적 차단. 보통 30분 후 자동 재시도 |
| LiPF6만 비어있음 | SMM API 변경됨. `data/lipf6_overrides.json`에 수동 입력 (README §3 참고) |
| Pages URL 404 | Pages 활성화 후 1~2분 기다리기. Settings → Pages에서 build 상태 확인 |

문제 생기면 Actions 탭의 실패한 workflow 로그를 캡처해서 알려주세요.
