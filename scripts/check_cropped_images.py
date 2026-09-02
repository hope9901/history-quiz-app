# -*- coding: utf-8 -*-
"""문항 이미지에서 선지가 잘린 것을 찾아낸다.

크롭 경계가 선지 도중을 지나가면 (1) 아래 여백이 crop_margins.py의 패딩(15px)보다
작아지고 (2) 보이는 선지 줄이 5개에 못 미친다. 두 신호를 함께 본다.

선지가 한 줄(연표·지도형)이나 2단(순서 나열형)으로 배열되거나 그림인 문항은
줄 수가 5로 잡히지 않으므로 '의심'으로만 보고하고, 최종 판정은 눈으로 확인한다.

사용법: python scripts/check_cropped_images.py
"""
import os
import sys
import glob

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "public", "images", "exams")

INK = 200          # 잉크로 볼 밝기 임계
MARGIN_MIN = 10    # 이보다 아래 여백이 좁으면 경계에 붙은 것
LINE_H = (17, 30)  # 선지 한 줄의 높이 범위
LINE_GAP = (34, 48)  # 선지 줄 사이 간격


def scan(path):
    """(보이는 선지 줄 수, 아래 여백)을 돌려준다."""
    a = np.array(Image.open(path).convert("L"))
    h, w = a.shape
    ink = a < INK
    row = ink.sum(axis=1)
    active = row > max(3, int(w * 0.015))

    left = np.full(h, -1)
    for y in np.where(active)[0]:
        c = np.where(ink[y])[0]
        if len(c):
            left[y] = c[0]

    lines, start = [], None
    for y in range(h):
        if active[y] and start is None:
            start = y
        elif not active[y] and start is not None:
            lines.append((start, y))
            start = None
    if start is not None:
        lines.append((start, h))

    cand = []
    for y0, y1 in lines:
        if LINE_H[0] <= y1 - y0 <= LINE_H[1]:
            xs = left[y0:y1]
            xs = xs[xs >= 0]
            if len(xs):
                cand.append((y0, int(np.median(xs))))

    count = 0
    if cand:
        chain = [cand[-1]]
        for c in reversed(cand[:-1]):
            py, px = chain[-1]
            if abs(c[1] - px) <= 5 and LINE_GAP[0] <= py - c[0] <= LINE_GAP[1]:
                chain.append(c)
            elif py - c[0] > LINE_GAP[1]:
                break
        count = len(chain)

    marked = np.where(row > max(2, int(w * 0.008)))[0]
    margin = h - 1 - int(marked.max()) if len(marked) else 0
    return count, margin


def main():
    paths = sorted(glob.glob(os.path.join(IMAGES, "*", "q*.jpg")))
    if not paths:
        print(f"[!] 이미지를 찾지 못했습니다: {IMAGES}")
        return 1
    suspects = []
    for p in paths:
        count, margin = scan(p)
        if count < 5 and margin < MARGIN_MIN:
            rnd = os.path.basename(os.path.dirname(p))
            qno = int(os.path.basename(p)[1:3])
            suspects.append((rnd, qno, count, margin))

    print(f"[*] 검사 {len(paths)}장")
    if not suspects:
        print("[+] 잘림 의심 문항 없음")
        return 0
    print(f"[!] 잘림 의심 {len(suspects)}건 — 눈으로 확인 필요")
    print("    (연표·지도형, 순서 나열형, 그림 선지 문항은 오탐일 수 있음)")
    for rnd, qno, count, margin in sorted(suspects, key=lambda r: (int(r[0]), r[1])):
        print(f"    {rnd}회 {qno:2d}번  보이는 선지 줄 {count}  아래 여백 {margin}px")
    return 0


if __name__ == "__main__":
    sys.exit(main())
