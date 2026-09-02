# -*- coding: utf-8 -*-
"""단/쪽 경계를 넘어간 선지 이어붙이기 회귀 테스트.

문제지는 2단 조판이라, 문항이 단 아래쪽에서 시작하면 선지 일부가 다음 단
(또는 다음 쪽) 최상단으로 넘어간다. crop_questions()가 그 부분을 찾아
이어 붙이는지 확인한다.

공식 PDF 없이 돌아가도록 합성 PDF를 만들어 검증한다.
사용법: python scripts/test_crop_continuation.py
"""
import os
import sys
import tempfile
import warnings
import importlib.util

warnings.filterwarnings("ignore")

import fitz  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "korea"  # 내장 CJK 폰트(동그라미 숫자 지원)


def load_builder():
    """공식 PDF가 없어도 되도록 모듈만 직접 적재한다."""
    spec = importlib.util.spec_from_file_location(
        "builder", os.path.join(HERE, "build_from_official_pdfs.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # 합성 PDF는 글자 수가 적어 OCR 경로로 빠지므로 텍스트 경로를 강제한다.
    mod.get_words_pages = lambda doc, rn: (
        [doc[i].get_text("words") for i in range(len(doc))], "text"
    )
    return mod


def make_pdf(path, spill):
    """2단 문제지를 흉내 낸다. spill=True면 3번의 선지 ④⑤가 오른쪽 단으로 넘어간다."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    L, R = 50, 320

    def put(x, y, s):
        page.insert_text((x, y), s, fontname=FONT, fontsize=10)

    def options(x, y, marks):
        for k, c in enumerate(marks):
            put(x, y + k * 16, f"{c} 선지 내용 {k + 1}")

    put(L, 80, "1. 첫 번째 문항입니다.")
    options(L, 100, "①②③④⑤")
    put(L, 200, "2. 두 번째 문항입니다.")
    options(L, 220, "①②③④⑤")
    put(L, 330, "3. 세 번째 문항입니다.")
    if spill:
        options(L, 350, "①②③")          # 앞 단에 3개만 남고
        put(R, 80, "④ 선지 내용 4")        # 나머지는 다음 단 최상단으로
        put(R, 96, "⑤ 선지 내용 5")
        top = 130
    else:
        options(L, 350, "①②③④⑤")        # 넘어가지 않는 경우
        top = 80
    put(R, top, "4. 네 번째 문항입니다.")
    options(R, top + 20, "①②③④⑤")
    put(295, 810, "1")  # 푸터
    doc.save(path)
    doc.close()


def text_lines(path):
    a = np.array(Image.open(path).convert("L"))
    ink = (a < 200).sum(axis=1)
    return sum(1 for i in range(1, len(ink)) if ink[i] > 0 and ink[i - 1] == 0)


def crop(mod, pdf, out):
    os.makedirs(out, exist_ok=True)
    try:
        mod.crop_questions(pdf, out, "test")
    except AssertionError:
        pass  # 합성본은 50문항이 아니라 문항 수 검사에서만 걸린다
    return out


def main():
    mod = load_builder()
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        # 1) 선지가 넘어간 경우 → 이어붙여 6줄(문두 + 선지 5)이 되어야 한다
        pdf = os.path.join(tmp, "spill.pdf")
        make_pdf(pdf, spill=True)
        out = crop(mod, pdf, os.path.join(tmp, "spill"))
        got = text_lines(os.path.join(out, "q03.jpg"))
        print(f"  넘어간 선지 복원      : q03 텍스트 줄 {got}개 (기대 6)")
        if got != 6:
            failures.append(f"이어붙이기 실패: q03 줄 수 {got} != 6")

        # 2) 넘어가지 않은 경우 → 다음 문항을 잘못 끌어오면 안 된다
        pdf2 = os.path.join(tmp, "plain.pdf")
        make_pdf(pdf2, spill=False)
        out2 = crop(mod, pdf2, os.path.join(tmp, "plain"))
        got2 = text_lines(os.path.join(out2, "q03.jpg"))
        print(f"  정상 문항 오염 없음   : q03 텍스트 줄 {got2}개 (기대 6)")
        if got2 != 6:
            failures.append(f"오검출: q03 줄 수 {got2} != 6")

        # 3) 넘어간 선지가 다음 문항 이미지에 중복으로 들어가면 안 된다
        got3 = text_lines(os.path.join(out, "q04.jpg"))
        print(f"  다음 문항 중복 없음   : q04 텍스트 줄 {got3}개 (기대 6)")
        if got3 != 6:
            failures.append(f"중복 포함: q04 줄 수 {got3} != 6")

    if failures:
        print("\n[!] 실패")
        for f in failures:
            print("   -", f)
        return 1
    print("\n[+] 통과: 단/쪽 경계를 넘어간 선지가 복원되고, 정상 문항은 영향 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
