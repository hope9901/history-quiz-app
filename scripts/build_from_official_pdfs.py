# -*- coding: utf-8 -*-
"""
국사편찬위원회 한국사능력검정시험 공식 기출 PDF에서 앱 데이터를 빌드합니다.

출처: 한국사능력검정시험 홈페이지 시험자료실 (https://www.historyexam.go.kr/pst/list.do?bbs=dat)
라이선스: 공공누리 제4유형 (출처표시·상업적 이용금지·변경금지)
  - 변경금지 조건을 지키기 위해 문항을 텍스트로 재구성하지 않고,
    문제지 원문을 문항 단위 이미지로 잘라 그대로 표시합니다.

지원 회차: 텍스트 레이어가 있는 문제지만 자동 분할 가능 (제72·75·76·77회 심화).
제73·74·78회 문제지는 스캔 이미지 PDF라 자동 분할이 불가능하여 제외합니다.

사용법: python scripts/build_from_official_pdfs.py
  (PDF는 PDF_DIR에 {회차}_exam.pdf / {회차}_answer.pdf 로 준비)
"""
import io
import os
import re
import json

import fitz  # PyMuPDF
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.environ.get(
    "EXAM_PDF_DIR",
    os.path.join(ROOT, "scripts", "official_pdfs"),
)
IMAGES_OUT = os.path.join(ROOT, "public", "images", "exams")
DATA_OUT = os.path.join(ROOT, "src", "data", "official_questions.json")

ROUNDS = ["58", "62", "70", "71", "72", "75", "76", "77"]
CIRCLED = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}

# 문제지 지면 구조: 2단 레이아웃이되 회차별 판형이 달라(729x1032 / 748x1091 등)
# 문항 번호 토큰의 x좌표 클러스터로 단 위치를 자동 감지한다.
COL_TOL = 5
FOOTER_MARGIN = 40  # 하단 페이지 번호 제외 영역
RENDER_ZOOM = 2.0


def isnum(s):
    return s.isascii() and s.isdigit()


def parse_answers(path):
    """정답표 PDF에서 (문항번호 → 정답, 배점)을 추출한다."""
    doc = fitz.open(path)
    words = doc[0].get_text("words")
    doc.close()
    toks = []
    for w in words:
        toks += re.findall(r"[①②③④⑤]|\d+", w[4])
    answers = {}
    i = 0
    while i < len(toks) - 2:
        a, b, c = toks[i], toks[i + 1], toks[i + 2]
        if isnum(a) and 1 <= int(a) <= 50:
            n = int(a)
            ans = CIRCLED.get(b) or (int(b) if isnum(b) and 1 <= int(b) <= 5 else None)
            sc = int(c) if isnum(c) and 1 <= int(c) <= 3 else None
            if ans and sc and n not in answers:
                answers[n] = {"answer": ans, "score": sc}
                i += 3
                continue
        i += 1
    assert len(answers) == 50, f"{path}: 50문항이 아닌 {len(answers)}문항 파싱됨"
    total = sum(v["score"] for v in answers.values())
    assert total == 100, f"{path}: 배점 합계 {total} != 100"
    return answers


def _in_span(x, span):
    return span[0] - COL_TOL <= x <= span[1] + COL_TOL


def detect_layout(doc):
    """문항 번호 토큰의 x좌표를 클러스터링해 좌/우 단의 번호 x범위를 감지한다.

    회차에 따라 번호가 우측 정렬되어 한 자리("1.")와 두 자리("10.") 번호의
    x가 다르므로, 클러스터는 (min_x, max_x) 스팬으로 다룬다.
    """
    from collections import Counter
    xs = Counter()
    for page in doc:
        for w in page.get_text("words"):
            if re.fullmatch(r"\d{1,2}\.", w[4]) and 1 <= int(w[4][:-1]) <= 50:
                xs[round(w[0])] += 1
    # 근접 x값(간격 12pt 이내)끼리 스팬으로 병합 후 빈도 상위 2개 선정
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


def find_questions(page, left_span, right_span):
    """페이지에서 문항 번호 토큰 위치를 찾아 (번호, 단, y좌표) 목록을 돌려준다."""
    found = []
    for w in page.get_text("words"):
        m = re.fullmatch(r"(\d{1,2})\.", w[4])
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


SHARED_HEADER_RE = re.compile(r"^\[?(\d{1,2})\s*[~∼〜]\s*(\d{1,2})\]?$")


def find_shared_headers(page, left_span, right_span):
    """'[47~48] 다음을 읽고 …' 형태의 공동 지문 헤더를 찾는다."""
    headers = []
    for w in page.get_text("words"):
        m = SHARED_HEADER_RE.fullmatch(w[4].replace(" ", ""))
        if not m:
            continue
        x0, y0 = w[0], w[1]
        if _in_span(x0, left_span):
            headers.append((int(m.group(1)), int(m.group(2)), "L", y0))
        elif _in_span(x0, right_span):
            headers.append((int(m.group(1)), int(m.group(2)), "R", y0))
    return headers


def render_clip(page, clip):
    pix = page.get_pixmap(matrix=fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM), clip=clip)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def crop_questions(exam_pdf, out_dir):
    """문제지 PDF를 문항 단위 이미지로 분할 저장하고 파일 목록을 돌려준다.

    공동 지문([NN~MM])이 있는 문항은 지문 이미지를 문항 위에 합성한다.
    """
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(exam_pdf)
    left_span, right_span, left_col, right_col = detect_layout(doc)
    saved = {}
    passages = {}  # 문항번호 → 지문 PIL 이미지
    for page in doc:
        page_content_bottom = page.rect.height - FOOTER_MARGIN
        marks = find_questions(page, left_span, right_span)
        headers = find_shared_headers(page, left_span, right_span)
        for col_key, (cx0, cx1) in (("L", left_col), ("R", right_col)):
            col = sorted([m for m in marks if m[1] == col_key], key=lambda m: m[2])
            # 해당 단 내 컨텐츠의 최하단 y (페이지 번호 제외)
            col_words_y = [
                w[3]
                for w in page.get_text("words")
                if cx0 <= w[0] <= cx1 and w[3] < page_content_bottom
            ]
            content_bottom = max(col_words_y) if col_words_y else page_content_bottom
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
                y_bot = (col[i + 1][2] - 10) if i + 1 < len(col) else content_bottom + 8
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
    doc.close()
    missing = [n for n in range(1, 51) if n not in saved]
    assert not missing, f"{exam_pdf}: 누락 문항 {missing}"
    return saved


def main():
    database = {}
    for r in ROUNDS:
        exam_pdf = os.path.join(PDF_DIR, f"{r}_exam.pdf")
        answer_pdf = os.path.join(PDF_DIR, f"{r}_answer.pdf")
        print(f"[*] 제{r}회 심화 처리 중...")
        answers = parse_answers(answer_pdf)
        out_dir = os.path.join(IMAGES_OUT, r)
        crop_questions(exam_pdf, out_dir)
        questions = []
        for n in range(1, 51):
            a = answers[n]
            circled = ["①", "②", "③", "④", "⑤"]
            questions.append(
                {
                    "id": n,
                    "epoch": "기출",
                    "score": a["score"],
                    "question": f"제{r}회 한국사능력검정시험(심화) {n}번",
                    "material": "",
                    "imageUrl": f"/images/exams/{r}/q{n:02d}.jpg",
                    "options": [f"{i+1}) {circled[i]}" for i in range(5)],
                    "answer": a["answer"],
                    "explanation": f"공식 정답표 기준 정답은 {circled[a['answer']-1]}({a['answer']}번)입니다. 국사편찬위원회는 기출문제 해설을 제공하지 않으므로, 상세 해설은 EBS 등 공개 강의 자료를 참고하세요.",
                    "summaryNote": "관련 시대의 핵심 개념은 [시대별 요약] 탭에서 복습할 수 있습니다.",
                }
            )
        database[r] = questions
        print(f"[+] 제{r}회: 50문항, 배점 합계 {sum(q['score'] for q in questions)}점")

    os.makedirs(os.path.dirname(DATA_OUT), exist_ok=True)
    with open(DATA_OUT, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    print(f"[+] 완료: {DATA_OUT} ({len(database)}개 회차 × 50문항)")


if __name__ == "__main__":
    main()
