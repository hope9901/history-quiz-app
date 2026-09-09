# -*- coding: utf-8 -*-
"""선지가 잘린 문항 이미지만 골라 원본 PDF에서 다시 잘라 붙인다.

왜 전체 재생성이 아니라 이 방식인가:
  기존 이미지는 Windows OCR 좌표로 만들어져 공동 지문 합성까지 잘 되어 있다.
  리눅스(Tesseract)로 전부 다시 만들면 그 품질을 따라가지 못해 멀쩡한 문항까지
  나빠진다. 그래서 잘린 문항만 손본다.

방법:
  1. 기존 이미지의 '행별 잉크량' 프로필을 PDF 각 단(段)에 슬라이딩 대조해
     문항이 지면 어디에 있었는지 찾는다(OCR 불필요).
  2. 그 단에서 본문의 진짜 끝을 찾는다. 페이지 번호는 폭이 단너비의 20%도
     되지 않으므로 폭으로 걸러낸다.
  3. 문항 시작부터 본문 끝까지 다시 잘라 저장하고 여백을 정리한다.

안전장치: 새 이미지가 기존보다 크지 않거나 매칭 품질이 나쁘면 건너뛴다.

사용법:
    python scripts/repair_truncated_images.py            # 알려진 잘림 문항 전부
    python scripts/repair_truncated_images.py 61 63      # 특정 회차만
"""
import os
import sys
import importlib.util

import numpy as np
from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    print("[!] PyMuPDF가 필요합니다: pip install pymupdf")
    raise SystemExit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "scripts")
PDF_DIR = os.environ.get("EXAM_PDF_DIR", os.path.join(HERE, "official_pdfs"))
IMAGES = os.path.join(ROOT, "public", "images", "exams")

ZOOM = 2.0
INK = 200            # 잉크로 볼 밝기
MIN_BODY_RATIO = 0.20  # 본문 줄로 인정할 최소 폭(단너비 대비) — 페이지 번호 제외용
PAD = 8              # 본문 끝 아래 여유
COARSE, FINE = 6, 1  # 프로필 대조 보폭(성긴 탐색 → 정밀 보정)

# 조사로 확인된 잘린 문항 (scripts/check_cropped_images.py + 육안 확인)
TRUNCATED = {
    "57": [48], "59": [46], "61": [44], "63": [44],
    "64": [44], "65": [48], "73": [48], "74": [44],
}


def page_gray(page):
    pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    return np.array(img)


def gutter_x(a):
    """가운데 부근에서 세로 잉크가 가장 적은 x = 두 단 사이 여백."""
    col = (a < INK).sum(axis=0)
    lo, hi = int(a.shape[1] * 0.40), int(a.shape[1] * 0.60)
    return lo + int(np.argmin(col[lo:hi]))


def row_profile(a):
    return (a < INK).sum(axis=1).astype(float)


def locate(doc, target):
    """기존 이미지가 지면 어디에서 잘려 나왔는지 찾는다.

    반환: (오차, 페이지번호, x0, x1, y_top) — 오차가 작을수록 확실하다.
    """
    P = row_profile(target)
    h = len(P)
    best = None
    for pno in range(len(doc)):
        a = page_gray(doc[pno])
        g = gutter_x(a)
        for x0, x1 in ((0, g), (g, a.shape[1])):
            C = row_profile(a[:, x0:x1])
            if len(C) <= h:
                continue
            for step in (COARSE, FINE):
                lo = 0 if step == COARSE else max(0, best[4] - COARSE)
                hi = len(C) - h if step == COARSE else min(len(C) - h, best[4] + COARSE)
                if step == FINE and (best is None or best[1] != pno or best[2] != x0):
                    break
                for y in range(lo, hi, step):
                    d = float(np.abs(C[y:y + h] - P).sum())
                    if best is None or d < best[0]:
                        best = (d, pno, x0, x1, y)
    return best


def body_bottom(a, x0, x1, y_from):
    """단 안에서 본문(선지)이 실제로 끝나는 y. 페이지 번호는 폭으로 걸러낸다."""
    strip = a[:, x0:x1] < INK
    width = x1 - x0
    rows = strip.sum(axis=1) > 3
    bands, start = [], None
    for y in range(len(rows)):
        if rows[y] and start is None:
            start = y
        elif not rows[y] and start is not None:
            if y - start >= 5:
                bands.append((start, y))
            start = None
    if start is not None:
        bands.append((start, len(rows)))
    bottom = None
    for b0, b1 in bands:
        if b1 <= y_from:
            continue
        cols = np.where(strip[b0:b1].any(axis=0))[0]
        if len(cols) and (cols.max() - cols.min()) >= width * MIN_BODY_RATIO:
            bottom = b1
    return bottom


def repair(round_no, qno, margins):
    pdf = os.path.join(PDF_DIR, f"{round_no}_exam.pdf")
    img_path = os.path.join(IMAGES, round_no, f"q{qno:02d}.jpg")
    if not os.path.exists(pdf):
        return None, f"문제지 PDF 없음 ({round_no}_exam.pdf)"
    if not os.path.exists(img_path):
        return None, "기존 이미지 없음"

    before = Image.open(img_path)
    target = np.array(before.convert("L"))
    doc = fitz.open(pdf)
    try:
        found = locate(doc, target)
        if found is None:
            return None, "지면에서 위치를 찾지 못함"
        dist, pno, x0, x1, y_top = found
        # 오차가 이미지 넓이 대비 과도하면 잘못 짚은 것으로 본다
        if dist / max(1, target.shape[0]) > target.shape[1] * 0.25:
            return None, f"매칭 신뢰도 낮음 (오차 {dist:.0f})"
        a = page_gray(doc[pno])
        bottom = body_bottom(a, x0, x1, y_top)
        if bottom is None or bottom <= y_top + target.shape[0]:
            return None, "이미 본문 끝까지 포함됨(잘림 아님)"
        crop = a[y_top:min(bottom + PAD, a.shape[0]), x0:x1]
        Image.fromarray(crop).convert("RGB").save(img_path, "JPEG", quality=87)
        margins.auto_crop_white_margins(img_path)
        after = Image.open(img_path)
        if after.size[1] <= before.size[1]:
            before.save(img_path, "JPEG", quality=87)  # 되돌린다
            return None, f"결과가 더 짧아 되돌림 ({before.size[1]}→{after.size[1]})"
        return (before.size, after.size, pno + 1), None
    finally:
        doc.close()


def main(argv):
    spec = importlib.util.spec_from_file_location("m", os.path.join(HERE, "crop_margins.py"))
    margins = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(margins)

    wanted = [a for a in argv if a.isdigit()]
    rounds = [r for r in sorted(TRUNCATED, key=int) if not wanted or r in wanted]
    fixed, skipped = [], []
    for r in rounds:
        for q in TRUNCATED[r]:
            ok, why = repair(r, q, margins)
            if ok:
                (bw, bh), (aw, ah), page = ok
                print(f"[+] {r}회 {q:2d}번  {bw}x{bh} → {aw}x{ah} (+{ah - bh}px, {page}쪽)")
                fixed.append(f"{r}-{q}")
            else:
                print(f"[-] {r}회 {q:2d}번  건너뜀: {why}")
                skipped.append(f"{r}-{q}")
    print()
    print(f"[+] 복구 {len(fixed)}건" + (f": {', '.join(fixed)}" if fixed else ""))
    if skipped:
        print(f"[-] 건너뜀 {len(skipped)}건: {', '.join(skipped)}")
    print("    확인: python scripts/check_cropped_images.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
