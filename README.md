history-quiz-app-chi.vercel.app

## 문항 데이터 출처

- 문항은 국사편찬위원회 주관 **한국사능력검정시험 제72·75·76·77회(심화)** 의 [공식 홈페이지 시험자료실](https://www.historyexam.go.kr/pst/list.do?bbs=dat)에서 공개한 문제지·정답표 원문을 문항 단위 이미지로 잘라 **변형 없이** 수록한 것입니다.
- 라이선스: [공공누리 제4유형](https://www.kogl.or.kr/info/license.do) (출처표시 · 상업적 이용금지 · 변경금지) — 본 프로젝트는 비영리 개인 학습용입니다.
- 제73·74·78회는 공개 문제지가 스캔 이미지 PDF라 문항 단위 자동 분할이 불가능하여 제외했습니다.
- 데이터 빌드 파이프라인: `scripts/build_from_official_pdfs.py`
  1. 시험자료실에서 내려받은 `{회차}_exam.pdf` / `{회차}_answer.pdf`를 `scripts/official_pdfs/`에 배치 (또는 `EXAM_PDF_DIR` 환경 변수로 경로 지정)
  2. 실행하면 정답표 파싱(배점 합계 100점 검증) 후 문제지를 문항 단위로 크롭하여 `public/images/exams/{회차}/qNN.jpg`와 `src/data/official_questions.json`을 생성

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
