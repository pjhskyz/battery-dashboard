# 배터리 소재 가격 대시보드

탄산리튬 (LC0), 니켈 (NI0), 구리 (HG=F), 알루미늄 (ALI=F), LiPF6 (SMM) 가격을
**자동으로 매일 수집·시각화**하는 production 대시보드.

> 데이터 소스: Sina Finance · Yahoo Finance · SMM (metal.com)
> 업데이트: GitHub Actions cron (평일 KST 18:00)
> 시각화: React + Recharts + Tailwind

```
battery-dashboard/
├── scraper/                 # Python 데이터 수집
│   ├── fetch_sina.py        # 탄산리튬, 니켈
│   ├── fetch_yahoo.py       # 구리, 알루미늄
│   ├── fetch_smm.py         # LiPF6 (best-effort + override)
│   └── main.py              # 오케스트레이터 → data/current.json
├── data/
│   ├── current.json         # ← 대시보드가 읽는 단 하나의 파일
│   └── lipf6_overrides.json # LiPF6 수동 입력 (SMM API 막힐 때 fallback)
├── dashboard/               # React (Vite) 앱
│   ├── BatteryDashboard.jsx
│   ├── src/main.jsx
│   ├── package.json
│   └── ...
├── .github/workflows/
│   └── update.yml           # 매일 cron으로 scraper/main.py 실행
└── requirements.txt
```

---

## 1) 빠른 시작 — 로컬 테스트

```bash
# Python scraper
pip install -r requirements.txt
python scraper/main.py
# → data/current.json 생성

# React dashboard
cd dashboard
npm install
npm run dev
# → http://localhost:5173 에서 확인
```

---

## 2) GitHub 배포 (권장)

### Step 1 — 레포 생성
```bash
gh repo create battery-dashboard --public --source=. --push
```

### Step 2 — Actions 권한 확인
**Settings → Actions → General → Workflow permissions → Read and write permissions** 체크.
이게 있어야 GitHub Actions가 `data/current.json`을 자동 커밋합니다.

### Step 3 — 첫 실행
- **Actions** 탭 → "Update battery prices" → **Run workflow** 수동 트리거
- 정상이면 1분 내 `data/current.json`이 commit으로 업데이트됨

### Step 4 — 대시보드 호스팅 (Vercel 권장)
```bash
cd dashboard
npm install -g vercel
vercel deploy --prod
```
배포 시 환경변수 `VITE_DATA_URL`을 GitHub raw URL로 설정:
```
VITE_DATA_URL=https://raw.githubusercontent.com/{USER}/battery-dashboard/main/data/current.json
```

또는 GitHub Pages로 배포 시 동일 레포에서 호스팅하면 상대경로 `./data/current.json`이
그대로 동작합니다.

---

## 3) LiPF6 데이터 처리

SMM의 chart XHR은 IP/계정 제한이 자주 걸립니다. 3-tier fallback 구조:

1. **자동 스크래핑** — `scraper/fetch_smm.py`가 metal.com 공개 API 호출 시도
2. **수동 override** — `data/lipf6_overrides.json`에 매주 SMM 화면 보고 직접 입력
   ```json
   [
     {"date": "2026-05-08",
      "avg_usd": 13025, "high_usd": 13260, "low_usd": 12790,
      "avg_cny": 100500, "high_cny": 102000, "low_cny": 99000}
   ]
   ```
   GitHub Actions 실행 시 자동 스크래핑이 빈 배열 반환하면 이 파일을 사용
3. **유료 SMM API 가입 시** — `fetch_smm.py`의 `SMM_API` 상수와 헤더에
   API 키 추가하면 자동 동작

---

## 4) 새 항목 추가하기

예: 텅스텐을 추가하려면

```python
# scraper/fetch_yahoo.py 에 추가
def fetch_tungsten():
    return _fetch("...", period="1y")  # 적절한 ticker

# scraper/main.py COMMODITIES 리스트에 추가
{
    "id": "tungsten",
    "title": "텅스텐 (...)",
    "unit": "USD/...",
    "source": "...",
    "source_url": "...",
    "decimals": 2,
    "type": "single",
    "fetch": fetch_tungsten,
},
```

대시보드는 `data/current.json`의 `commodities` dict에 새 키만 추가하면
React 코드 수정 없이 자동으로 카드가 추가됩니다 (`order` 배열에만 ID 추가).

---

## 5) 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `Sina returned 403` | User-Agent 변경 필요. `fetch_sina.py` HEADERS 수정 |
| `yfinance` empty | Yahoo가 일시적으로 ticker 차단. 5분 대기 후 재시도 |
| `lipf6_*` 비어있음 | `data/lipf6_overrides.json`에 직접 입력 (위 §3 참고) |
| Returns가 `null` | 시계열이 N일 미만 (1W=5d, 1M=22d, 3M=66d, 6M=132d 필요) |
| GitHub Actions 커밋 실패 | Settings → Actions → Workflow permissions를 "Read and write"로 |
| 대시보드 빈 화면 | DevTools → Network 탭에서 `current.json` fetch 상태 확인 |

---

## 6) 데이터 검증

스크래퍼가 잘 돌아가는지 확인:
```bash
python scraper/main.py | tail -20
```

기대 출력:
```
✓ lithium      245 pts | latest=196560.0 | 1D=-1.26% 6M=140.76%
✓ nickel       246 pts | latest=146450.0 | 1D=-2.17% 6M=21.47%
✓ copper       251 pts | latest=6.249 | 1D=1.98% 6M=25.91%
✓ aluminum     249 pts | latest=3507.0 | 1D=0.78% 6M=26.94%
✓ lipf6_usd    21 pts | latest=13025.11 | 1D=0.46%
✓ lipf6_cny    36 pts | latest=100500 | 1D=0.50%
```

---

## 7) 라이선스 & 데이터 출처

- 가격 데이터는 각 출처(Sina/Yahoo/SMM)의 라이선스를 따름
- 본 코드는 MIT
- SMM 데이터의 상업적 재배포는 SMM 약관에 따라 제한될 수 있음. 개인 트래킹용으로 사용 권장.
