# -*- coding: utf-8 -*-
"""
국사편찬위원회 한국사능력검정시험 공식 기출 PDF에서 앱 데이터를 빌드합니다.

출처: 한국사능력검정시험 홈페이지 시험자료실 (https://www.historyexam.go.kr/pst/list.do?bbs=dat)
라이선스: 공공누리 제4유형 (출처표시·상업적 이용금지·변경금지)
  - 변경금지 조건을 지키기 위해 문항을 텍스트로 재구성하지 않고,
    문제지 원문을 문항 단위 이미지로 잘라 그대로 표시합니다.

문항 위치 감지:
  - 텍스트 레이어가 있는 문제지: PDF 텍스트 좌표 사용
  - 스캔 이미지 문제지: Windows 내장 OCR(scripts/ocr_words.ps1)로 단어 좌표 추출
    (OCR 결과는 PDF_DIR/ocr_cache/{회차}.json 에 캐시)

사용법: python scripts/build_from_official_pdfs.py
  (PDF는 PDF_DIR에 {회차}_exam.pdf / {회차}_answer.pdf 로 준비)
"""
import io
import os
import re
import json
import subprocess

import fitz  # PyMuPDF
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.environ.get(
    "EXAM_PDF_DIR",
    os.path.join(ROOT, "scripts", "official_pdfs"),
)
IMAGES_OUT = os.path.join(ROOT, "public", "images", "exams")
DATA_OUT = os.path.join(ROOT, "src", "data", "official_questions.json")
OCR_SCRIPT = os.path.join(ROOT, "scripts", "ocr_words.ps1")

ROUNDS = [
    "57", "58", "59", "60", "61", "62", "63", "64", "65", "66", "67",
    "68", "69", "70", "71", "72", "73", "74", "75", "76", "77", "78",
]
CIRCLED = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}

# 문제지 지면 구조: 2단 레이아웃이되 회차별 판형이 달라(729x1032 / 748x1091 등)
# 문항 번호 토큰의 x좌표 클러스터로 단 위치를 자동 감지한다.
COL_TOL = 6
FOOTER_MARGIN = 25  # 페이지 최하단 여백
RENDER_ZOOM = 2.0

# 페이지 하단 번호("12", "1/12" 등) — 컨텐츠 최하단 계산에서 제외
FOOTER_WORD_RE = re.compile(r"^[\d/\\|]+$")


def is_footer_word(w, page_h):
    return w[1] > page_h * 0.88 and bool(FOOTER_WORD_RE.fullmatch(w[4]))


def isnum(s):
    return s.isascii() and s.isdigit()


def parse_answers(path):
    """정답표 PDF에서 (문항번호 → 정답, 배점)을 추출한다.

    정답표는 행 우선 5그룹 표(1,11,21,31,41 / 2,12,22,32,42 / …)이므로
    기대 번호 순서대로 (번호, 정답, 배점) 3연속 토큰을 매칭한다.
    잡음 토큰(머릿말 '[양식2]' 등)은 기대 번호와 불일치 시 건너뛴다.
    """
    doc = fitz.open(path)
    words = doc[0].get_text("words")
    doc.close()
    toks = []
    for w in words:
        toks += re.findall(r"[①②③④⑤]|없음|\d+", w[4])

    expected = [row + 10 * g for row in range(1, 11) for g in range(5)]

    def to_ans(t):
        if t in CIRCLED:
            return CIRCLED[t]
        if t == "없음":
            return 0  # 문항 오류 판정 → 응시자 전원 정답 처리
        return int(t) if isnum(t) and 1 <= int(t) <= 5 else None

    answers = {}
    i = 0
    for n in expected:
        # 기대 번호 n 을 찾을 때까지 토큰 스킵 (직후 정답·배점이 유효해야 매칭)
        while i < len(toks) - 2:
            if isnum(toks[i]) and int(toks[i]) == n:
                ans = to_ans(toks[i + 1])
                sc = int(toks[i + 2]) if isnum(toks[i + 2]) and 1 <= int(toks[i + 2]) <= 3 else None
                if ans is not None and sc:
                    answers[n] = {"answer": ans, "score": sc}
                    i += 3
                    break
            i += 1
        else:
            break

    assert len(answers) == 50, f"{path}: 50문항이 아닌 {len(answers)}문항 파싱됨"
    total = sum(v["score"] for v in answers.values())
    assert total == 100, f"{path}: 배점 합계 {total} != 100"
    return answers


# ── 단어 좌표 추출 (텍스트 레이어 / OCR) ─────────────────────────
def has_text_layer(doc):
    return sum(len(doc[i].get_text().strip()) for i in range(min(3, len(doc)))) > 500


def ocr_words_pages(doc, round_no):
    """스캔 PDF의 각 페이지를 렌더링해 Windows OCR로 단어 좌표를 얻는다."""
    cache = os.path.join(PDF_DIR, "ocr_cache", f"{round_no}.json")
    if not os.path.exists(cache):
        png_dir = os.path.join(PDF_DIR, "ocr_cache", f"{round_no}_pages")
        os.makedirs(png_dir, exist_ok=True)
        for i, page in enumerate(doc):
            out = os.path.join(png_dir, f"p{i+1:02d}.png")
            if not os.path.exists(out):
                page.get_pixmap(matrix=fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM)).save(out)
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", OCR_SCRIPT, "-Dir", png_dir, "-Out", cache],
            capture_output=True, text=True, timeout=900,
        )
        if r.returncode != 0 or not os.path.exists(cache):
            raise RuntimeError(f"OCR 실패 (제{round_no}회): {r.stderr[:500]}")
    with open(cache, encoding="utf-8-sig") as f:
        data = json.load(f)
    pages = []
    for i in range(len(doc)):
        key = f"p{i+1:02d}.png"
        words = []
        for w in data.get(key, []):
            # 픽셀 좌표(zoom 2) → PDF 포인트 좌표
            words.append((w[0] / RENDER_ZOOM, w[1] / RENDER_ZOOM,
                          w[2] / RENDER_ZOOM, w[3] / RENDER_ZOOM, w[4]))
        pages.append(words)
    return pages


def get_words_pages(doc, round_no):
    """페이지별 단어 목록 [(x0,y0,x1,y1,text), …] 과 모드('text'|'ocr')를 돌려준다."""
    if has_text_layer(doc):
        return [page.get_text("words") for page in doc], "text"
    return ocr_words_pages(doc, round_no), "ocr"


# ── 지면 구조 감지 ───────────────────────────────────────────────
def _in_span(x, span):
    return span[0] - COL_TOL <= x <= span[1] + COL_TOL


NUM_RE = re.compile(r"(\d{1,2})\.")


def detect_layout(words_pages):
    """문항 번호 토큰의 x좌표를 클러스터링해 좌/우 단의 번호 x범위를 감지한다.

    회차에 따라 번호가 우측 정렬되어 한 자리("1.")와 두 자리("10.") 번호의
    x가 다르므로, 클러스터는 (min_x, max_x) 스팬으로 다룬다.
    """
    from collections import Counter
    xs = Counter()
    for words in words_pages:
        for w in words:
            m = NUM_RE.fullmatch(w[4])
            if m and 1 <= int(m.group(1)) <= 50:
                xs[round(w[0])] += 1
    clusters = []
    for x, c in sorted(xs.items()):
        if clusters and x - clusters[-1]["max"] <= 12:
            clusters[-1]["max"] = x
            clusters[-1]["count"] += c
        else:
            clusters.append({"min": x, "max": x, "count": c})
    top2 = sorted(sorted(clusters, key=lambda c: -c["count"])[:2], key=lambda c: c["min"])
    assert len(top2) == 2, f"2단 레이아웃 감지 실패: {clusters}"
    left_span = (top2[0]["min"], top2[0]["max"])
    right_span = (top2[1]["min"], top2[1]["max"])
    col_w = right_span[0] - left_span[0]
    left_col = (left_span[0] - 7, right_span[0] - 11)
    right_col = (right_span[0] - 7, right_span[0] + col_w - 11)
    return left_span, right_span, left_col, right_col


def find_questions(words, left_span, right_span):
    """단어 목록에서 문항 번호 토큰 위치를 찾아 (번호, 단, y좌표) 목록을 돌려준다."""
    found = []
    for w in words:
        m = NUM_RE.fullmatch(w[4])
        if not m:
            continue
        n = int(m.group(1))
        if not 1 <= n <= 50:
            continue
        x0, y0 = w[0], w[1]
        if _in_span(x0, left_span):
            found.append((n, "L", y0))
        elif _in_span(x0, right_span):
            found.append((n, "R", y0))
    return found


SHARED_RANGE_RE = re.compile(r"\[?(\d{1,2})\s*[~∼〜\-]\s*(\d{1,2})\]?")


def find_shared_headers(words, left_col, right_col):
    """'[47~48] 다음을 읽고 물음에 답하시오' 형태의 공동 지문 헤더를 찾는다.

    '물음에' 토큰이 있는 줄을 앵커와 같은 단(column) 범위 안에서만 재구성한 뒤
    [NN~MM] 범위를 파싱한다. (텍스트 PDF와 OCR 결과 모두에서 동작)
    """
    headers = []
    anchors = [w for w in words if "물음에" in w[4]]
    for a in anchors:
        if left_col[0] - 5 <= a[0] <= left_col[1]:
            col_key, (cx0, cx1) = "L", left_col
        elif right_col[0] - 5 <= a[0] <= right_col[1]:
            col_key, (cx0, cx1) = "R", right_col
        else:
            continue
        line = [w for w in words if abs(w[1] - a[1]) <= 8 and cx0 - 5 <= w[0] <= cx1]
        line.sort(key=lambda w: w[0])
        text = "".join(w[4] for w in line)
        m = SHARED_RANGE_RE.search(text)
        if not m:
            continue
        n1, n2 = int(m.group(1)), int(m.group(2))
        if not (1 <= n1 < n2 <= 50 and n2 - n1 <= 3):
            continue
        y0 = min(w[1] for w in line)
        headers.append((n1, n2, col_key, y0))
    return headers


def text_in_clip(words, clip):
    return " ".join(w[4] for w in words if clip.y0 <= w[1] <= clip.y1 and clip.x0 <= w[0] <= clip.x1)


# ── 시대 자동 분류 ──────────────────────────────────────────────
# 문항 텍스트의 키워드 점수로 시대를 추정한다. (시대별 요약 탭과 동일한 9분류)
# 한능검 문항은 대체로 시대순 배열이므로, 미분류 문항은 앞 문항의 시대로 보간한다.
EPOCH_ORDER = ["선사", "삼국", "남북국", "고려", "조선 전기", "조선 후기", "근대", "일제강점기", "현대"]

EPOCH_KEYWORDS = {
    "선사": [
        "구석기", "신석기", "청동기", "철기 시대", "주먹도끼", "빗살무늬", "반달 돌칼", "고인돌",
        "비파형", "세형 동검", "가락바퀴", "움집", "막집", "고조선", "위만", "단군", "8조",
        "부여", "옥저", "동예", "삼한", "영고", "서옥제", "민며느리", "사출도", "소도", "천군",
        "책화", "무천", "우가", "마가", "동굴", "뗀석기", "간석기",
    ],
    "삼국": [
        "고구려", "백제", "가야", "광개토", "장수왕", "근초고", "무령왕", "성왕", "진흥왕",
        "법흥왕", "지증왕", "소수림왕", "내물", "살수", "안시성", "을지문덕", "연개소문", "계백",
        "황산벌", "김유신", "김춘추", "화랑", "첨성대", "미륵사", "황룡사", "칠지도", "웅진",
        "사비", "마립간", "순수비", "평양 천도", "한성 함락", "관산성", "대가야", "금관가야",
        "수로", "우산국", "이사부", "이차돈", "백강", "매소성", "기벌포", "나당", "무용총",
        "금동대향로", "돌무지덧널", "천마총", "22담로", "정림사지",
    ],
    "남북국": [
        "통일 신라", "신문왕", "성덕왕", "경덕왕", "원성왕", "독서삼품", "관료전", "녹읍",
        "9주 5소경", "국학", "김흠돌", "장보고", "청해진", "발해", "대조영", "해동성국",
        "상경", "정당성", "3성 6부", "인안", "대흥", "장문휴", "원효", "의상", "혜초",
        "최치원", "견훤", "궁예", "후백제", "후고구려", "석굴암", "불국사", "석가탑",
        "무구정광", "성덕대왕", "김헌창", "원종과 애노", "호족", "6두품", "선종", "풍수지리",
        "이불병좌상", "정혜공주",
    ],
    "고려": [
        "고려", "왕건", "광종", "노비안검", "쌍기", "최승로", "시무 28조", "12목",
        "서희", "강동 6주", "강감찬", "귀주", "윤관", "별무반", "동북 9성", "이자겸", "묘청",
        "서경 천도", "무신", "정중부", "최충헌", "교정도감", "최우", "정방", "만적", "망이",
        "삼별초", "배중손", "김윤후", "처인성", "팔만대장경", "강화 천도", "쌍성총관부",
        "공민왕", "전민변정", "신돈", "기철", "권문세족", "신진 사대부", "위화도", "과전법",
        "전시과", "벽란도", "활구", "은병", "상감", "청자", "직지", "흥덕사", "삼국사기",
        "삼국유사", "일연", "김부식", "의천", "지눌", "요세", "혜심", "성리학", "안향",
        "정동행성", "도평의사사", "주심포", "부석사 무량수전", "관촉사", "월정사",
    ],
    "조선 전기": [
        "조선", "이성계", "정도전", "태종", "호패", "6조 직계", "세종", "집현전", "훈민정음",
        "칠정산", "장영실", "측우기", "앙부일구", "자격루", "4군 6진", "세조", "직전법",
        "계유정난", "성종", "경국대전", "홍문관", "사헌부", "사간원", "삼사", "무오사화",
        "갑자사화", "기묘사화", "을사사화", "조광조", "현량과", "위훈", "사림", "훈구", "서원",
        "향약", "이황", "이이", "성학집요", "성학십도", "임진왜란", "이순신", "한산도",
        "학익진", "명량", "노량", "곽재우", "김시민", "진주", "행주", "권율", "의병",
        "광해군", "중립 외교", "인조반정", "정묘호란", "병자호란", "남한산성", "삼전도",
        "효종", "북벌", "나선 정벌", "동의보감", "허준", "몽유도원도", "분청사기", "삼강행실도",
        "농사직설", "향약집성방", "조선왕조실록", "승정원",
    ],
    "조선 후기": [
        "숙종", "예송", "환국", "영조", "탕평", "균역법", "정조", "규장각", "초계문신",
        "장용영", "수원 화성", "신해통공", "금난전권", "영정법", "대동법", "공인", "모내기",
        "이앙법", "광작", "상평통보", "전황", "송상", "만상", "내상", "경강", "보부상",
        "덕대", "공명첩", "납속", "실학", "유형원", "이익", "정약용", "목민심서", "여전론",
        "거중기", "박지원", "열하일기", "박제가", "북학의", "홍대용", "지전설", "유수원",
        "유득공", "발해고", "김정희", "추사", "세한도", "금석과안록", "대동여지도", "김정호",
        "동사강목", "안정복", "세도 정치", "비변사", "삼정", "홍경래", "임술", "백낙신",
        "삼정이정청", "안핵사", "동학", "최제우", "최시형", "천주교", "신유박해", "황사영",
        "판소리", "탈춤", "한글 소설", "민화", "진경산수", "인왕제색", "김홍도", "신윤복",
        "정선", "속대전", "백두산정계비",
    ],
    "근대": [
        "흥선", "대원군", "경복궁 중건", "당백전", "서원 철폐", "호포", "병인박해", "병인양요",
        "신미양요", "제너럴셔먼", "오페르트", "척화비", "어재연", "외규장각", "운요호",
        "강화도 조약", "조일", "개항", "수신사", "조사 시찰단", "영선사", "보빙사", "기기창",
        "통리기무아문", "별기군", "위정척사", "최익현", "이만손", "만인소", "조선책략",
        "임오군란", "제물포", "갑신정변", "우정총국", "톈진", "거문도", "동학 농민", "전봉준",
        "고부", "황토현", "전주 화약", "집강소", "우금치", "군국기무처", "갑오개혁", "홍범 14조",
        "을미사변", "단발령", "아관파천", "독립 협회", "독립문", "만민 공동회", "헌의 6조",
        "대한 제국", "광무", "환구단", "지계", "원수부", "러일", "한일 의정서", "메가타",
        "스티븐스", "을사늑약", "통감부", "헤이그", "정미", "군대 해산", "13도 창의군",
        "신돌석", "안중근", "이토", "신민회", "안창호", "양기탁", "오산 학교", "대성 학교",
        "105인", "국채 보상", "서상돈", "대한매일신보", "베델", "황성신문", "독사신론",
        "육영 공원", "원산 학사", "경인선", "경부선", "전차", "광혜원", "제중원", "덕수궁",
        "화폐 정리",
    ],
    "일제강점기": [
        "조선 총독부", "무단 통치", "헌병 경찰", "태형", "토지 조사", "회사령", "산미 증식",
        "문화 통치", "황국 신민", "창씨", "신사 참배", "내선일체", "국가 총동원", "공출",
        "징용", "위안부", "3·1 운동", "삼일 운동", "유관순", "제암리", "임시 정부", "임시정부",
        "연통제", "교통국", "독립 공채", "구미 위원부", "국민 대표 회의", "김구", "한인 애국단",
        "이봉창", "윤봉길", "훙커우", "봉오동", "홍범도", "청산리", "김좌진", "북로 군정서",
        "간도 참변", "자유시", "참의부", "정의부", "신민부", "미쓰야", "의열단", "김원봉",
        "조선 혁명 선언", "김익상", "김상옥", "나석주", "조선 의용대", "조선 혁명군", "양세봉",
        "한국 독립군", "지청천", "영릉가", "쌍성보", "대전자령", "한국광복군", "광복군",
        "대일 선전", "국내 진공", "물산 장려", "조만식", "민립 대학", "브나로드", "6·10 만세",
        "광주 학생", "신간회", "근우회", "정우회", "형평", "암태도", "원산 총파업", "소작 쟁의",
        "조선어 학회", "조선어학회", "한글 맞춤법", "신채호", "조선상고사", "박은식",
        "한국통사", "진단 학회", "아리랑", "나운규", "손기정", "카프", "토월회", "원각사",
    ],
    "현대": [
        "광복", "8·15", "건국 준비 위원회", "여운형", "모스크바", "신탁", "미소 공동",
        "좌우 합작", "남북 협상", "정읍", "5·10 총선", "제헌", "반민족", "반민특위",
        "농지 개혁", "제주 4·3", "여수", "6·25", "인천 상륙", "1·4 후퇴", "정전 협정",
        "한미 상호", "발췌 개헌", "사사오입", "진보당", "조봉암", "3·15", "4·19", "이승만",
        "장면", "5·16", "박정희", "한일 협정", "6·3", "베트남 파병", "브라운", "경제 개발",
        "경부 고속", "새마을", "전태일", "3선 개헌", "유신", "긴급 조치", "통일 주체",
        "YH", "부마", "10·26", "12·12", "신군부", "5·18", "광주 민주화", "전두환", "4·13",
        "6월 민주", "박종철", "이한열", "6·29", "직선제", "노태우", "서울 올림픽", "북방",
        "김영삼", "금융 실명", "OECD", "외환 위기", "IMF", "김대중", "금 모으기", "햇볕",
        "7·4 남북", "남북 기본 합의", "비핵화 공동", "6·15", "개성 공단", "금강산", "10·4",
        "이산가족", "노무현", "판문점 선언",
    ],
}


def classify_epoch(text):
    """문항 텍스트를 키워드 점수로 시대 분류한다. 점수가 없으면 None."""
    compact = text.replace(" ", "")
    scores = {}
    for epoch, kws in EPOCH_KEYWORDS.items():
        s = 0
        for kw in kws:
            if kw.replace(" ", "") in compact:
                s += 1
        if s:
            scores[epoch] = s
    if not scores:
        return None
    return max(scores, key=lambda e: scores[e])


def interpolate_epochs(epochs):
    """미분류(None) 문항을 앞 문항(없으면 뒤 문항)의 시대로 보간한다."""
    out = list(epochs)
    for i in range(len(out)):
        if out[i] is None:
            out[i] = out[i - 1] if i > 0 and out[i - 1] else None
    for i in range(len(out) - 1, -1, -1):
        if out[i] is None:
            out[i] = out[i + 1] if i + 1 < len(out) and out[i + 1] else "기출"
    return out


# ── 문항 크롭 ────────────────────────────────────────────────────
def render_clip(page, clip):
    pix = page.get_pixmap(matrix=fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM), clip=clip)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def crop_questions(exam_pdf, out_dir, round_no):
    """문제지 PDF를 문항 단위 이미지로 분할 저장한다.

    공동 지문([NN~MM])이 있는 문항은 지문 이미지를 문항 위에 합성한다.
    반환: (모드, 문항번호→텍스트 사전)
    """
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(exam_pdf)
    words_pages, mode = get_words_pages(doc, round_no)
    left_span, right_span, left_col, right_col = detect_layout(words_pages)
    saved = {}
    texts = {}  # 문항번호 → 문항 텍스트 (시대 분류용)
    passages = {}  # 문항번호 → 지문 PIL 이미지
    for pno, page in enumerate(doc):
        words = words_pages[pno]
        page_content_bottom = page.rect.height - FOOTER_MARGIN
        marks = find_questions(words, left_span, right_span)
        headers = find_shared_headers(words, left_col, right_col)
        for col_key, (cx0, cx1) in (("L", left_col), ("R", right_col)):
            col = sorted([m for m in marks if m[1] == col_key], key=lambda m: m[2])
            # 단의 마지막 문항은 페이지 번호(푸터) 직전까지 포함시킨다.
            # (그림 선지처럼 텍스트가 없는 영역이 잘리지 않도록 텍스트 최하단 대신 푸터 기준 사용)
            footer_ys = [
                w[1] for w in words
                if cx0 <= w[0] <= cx1 and is_footer_word(w, page.rect.height)
            ]
            content_bottom = (min(footer_ys) - 6) if footer_ys else page_content_bottom
            # 공동 지문: 헤더 y부터 범위 시작 문항 번호 y 직전까지
            for h_start, h_end, h_col, h_y in headers:
                if h_col != col_key:
                    continue
                first_q = next((m for m in col if m[0] == h_start), None)
                if first_q is None:
                    continue
                clip = fitz.Rect(cx0, h_y - 6, cx1, first_q[2] - 10)
                img = render_clip(page, clip)
                for n in range(h_start, h_end + 1):
                    passages[n] = img
            for i, (n, _, y0) in enumerate(col):
                y_top = y0 - 8
                y_bot = (col[i + 1][2] - 10) if i + 1 < len(col) else content_bottom
                clip = fitz.Rect(cx0, y_top, cx1, min(y_bot, page_content_bottom))
                img = render_clip(page, clip)
                if n in passages:
                    p_img = passages[n]
                    gap = 14
                    combo = Image.new(
                        "RGB", (max(p_img.width, img.width), p_img.height + gap + img.height), "white"
                    )
                    combo.paste(p_img, (0, 0))
                    combo.paste(img, (0, p_img.height + gap))
                    img = combo
                fname = f"q{n:02d}.jpg"
                img.convert("RGB").save(os.path.join(out_dir, fname), "JPEG", quality=87)
                saved[n] = fname
                texts[n] = texts.get(n, "") + " " + text_in_clip(words, clip)
    doc.close()
    missing = [n for n in range(1, 51) if n not in saved]
    assert not missing, f"{exam_pdf}: 누락 문항 {missing}"
    return mode, texts


def main():
    database = {}
    failed = []
    for r in ROUNDS:
        exam_pdf = os.path.join(PDF_DIR, f"{r}_exam.pdf")
        answer_pdf = os.path.join(PDF_DIR, f"{r}_answer.pdf")
        print(f"[*] 제{r}회 심화 처리 중...")
        try:
            answers = parse_answers(answer_pdf)
            out_dir = os.path.join(IMAGES_OUT, r)
            mode, texts = crop_questions(exam_pdf, out_dir, r)
        except Exception as e:
            print(f"[!] 제{r}회 실패: {e}")
            failed.append(r)
            continue
        # 시대 자동 분류 (키워드 점수 → 시대순 보간)
        raw_epochs = [classify_epoch(texts.get(n, "")) for n in range(1, 51)]
        epochs = interpolate_epochs(raw_epochs)
        classified = sum(1 for e in raw_epochs if e)
        questions = []
        for n in range(1, 51):
            a = answers[n]
            epoch = epochs[n - 1]
            circled = ["①", "②", "③", "④", "⑤"]
            questions.append(
                {
                    "id": n,
                    "epoch": epoch,
                    "score": a["score"],
                    "question": f"제{r}회 한국사능력검정시험(심화) {n}번",
                    "material": "",
                    "imageUrl": f"/images/exams/{r}/q{n:02d}.jpg",
                    "options": [f"{i+1}) {circled[i]}" for i in range(5)],
                    "answer": a["answer"],
                    "explanation": (
                        "이 문항은 공식 이의심사 결과 오류로 판정되어 '정답 없음'(응시자 전원 정답)으로 처리되었습니다."
                        if a["answer"] == 0
                        else f"공식 정답표 기준 정답은 {circled[a['answer']-1]}({a['answer']}번)입니다. 국사편찬위원회는 기출문제 해설을 제공하지 않으므로, 상세 해설은 EBS 등 공개 강의 자료를 참고하세요."
                    ),
                    "summaryNote": f"자동 추정 시대: {epoch} — [시대별 요약] 탭의 '{epoch}' 항목에서 빈출 선지 포인트를 복습하세요.",
                }
            )
        database[r] = questions
        print(f"[+] 제{r}회({mode}): 50문항, 배점 합계 {sum(q['score'] for q in questions)}점, "
              f"시대 직접 분류 {classified}/50")

    os.makedirs(os.path.dirname(DATA_OUT), exist_ok=True)
    with open(DATA_OUT, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    print(f"[+] 완료: {DATA_OUT} ({len(database)}개 회차 × 50문항)")
    if failed:
        print(f"[!] 실패 회차: {failed}")


if __name__ == "__main__":
    main()
