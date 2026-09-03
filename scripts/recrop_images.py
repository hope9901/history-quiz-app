# -*- coding: utf-8 -*-
"""공식 PDF에서 문항 이미지만 다시 잘라낸다(데이터베이스는 건드리지 않는다).

build_from_official_pdfs.py의 main()은 앱 데이터 전체를 다시 만들기 때문에
22개 회차의 문제지·정답표 PDF가 모두 필요하다. 반면 선지가 잘린 이미지를
고치는 데 필요한 것은 문제지 PDF뿐이므로, 이 스크립트는 이미지만 다시 만든다.

준비:
    scripts/official_pdfs/{회차}_exam.pdf     (정답표 PDF는 필요 없음)
    예) scripts/official_pdfs/74_exam.pdf

사용법:
    python scripts/recrop_images.py              # 넣어둔 문제지 PDF를 모두 처리
    python scripts/recrop_images.py 74 73 65     # 특정 회차만 처리

끝난 뒤에는 python scripts/check_cropped_images.py 로 잘림이 사라졌는지 확인한다.
"""
import os
import sys
import glob
import shutil
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "scripts")
IMAGES_OUT = os.path.join(ROOT, "public", "images", "exams")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv):
    builder = load("build_from_official_pdfs")
    margins = load("crop_margins")
    pdf_dir = builder.PDF_DIR

    wanted = [a for a in argv if a.isdigit()]
    found = sorted(
        (os.path.basename(p).split("_")[0] for p in glob.glob(os.path.join(pdf_dir, "*_exam.pdf"))),
        key=int,
    )
    rounds = [r for r in found if not wanted or r in wanted]

    if not rounds:
        print(f"[!] 문제지 PDF를 찾지 못했습니다: {pdf_dir}/{{회차}}_exam.pdf")
        if wanted:
            print(f"    요청한 회차: {', '.join(wanted)} / 발견된 회차: {', '.join(found) or '없음'}")
        print("    공식 자료실(한국사능력검정시험 시험자료실)에서 문제지를 내려받아 위 경로에 두세요.")
        return 1

    missing = [r for r in wanted if r not in found]
    if missing:
        print(f"[!] PDF가 없어 건너뜁니다: {', '.join(missing)}회")

    ok, failed = [], []
    for r in rounds:
        exam_pdf = os.path.join(pdf_dir, f"{r}_exam.pdf")
        out_dir = os.path.join(IMAGES_OUT, r)
        backup = out_dir + ".bak"
        print(f"[*] 제{r}회 이미지 재생성...")
        if os.path.isdir(out_dir):
            shutil.rmtree(backup, ignore_errors=True)
            shutil.copytree(out_dir, backup)
        try:
            mode, _ = builder.crop_questions(exam_pdf, out_dir, r)
            for p in sorted(glob.glob(os.path.join(out_dir, "q*.jpg"))):
                margins.auto_crop_white_margins(p)
            print(f"    · 완료 (좌표 추출 방식: {mode})")
            shutil.rmtree(backup, ignore_errors=True)
            ok.append(r)
        except Exception as e:
            print(f"[!] 제{r}회 실패: {e}")
            if os.path.isdir(backup):  # 원래 이미지로 되돌린다
                shutil.rmtree(out_dir, ignore_errors=True)
                shutil.move(backup, out_dir)
                print("    · 기존 이미지를 그대로 되돌렸습니다.")
            failed.append(r)

    print()
    print(f"[+] 성공 {len(ok)}개 회차" + (f": {', '.join(ok)}" if ok else ""))
    if failed:
        print(f"[!] 실패 {len(failed)}개 회차: {', '.join(failed)}")
        print("    스캔본 회차는 좌표 추출에 Windows OCR(scripts/ocr_words.ps1)이 필요합니다.")
    print("    확인: python scripts/check_cropped_images.py")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
