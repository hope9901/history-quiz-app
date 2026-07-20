import React from "react";
import { Check, ClipboardCheck, CornerDownRight } from "lucide-react";

interface Question {
  id: number;
  answer: number;
}

interface OMRSheetProps {
  questions: Question[];
  answers: Record<number, number | null>;
  currentQuestionId: number;
  onJumpToQuestion: (index: number) => void;
  onMarkAnswer: (questionId: number, answerNum: number) => void;
  onSubmit: () => void;
  isReviewMode?: boolean;
}

export const OMRSheet: React.FC<OMRSheetProps> = ({
  questions,
  answers,
  currentQuestionId,
  onJumpToQuestion,
  onMarkAnswer,
  onSubmit,
  isReviewMode = false,
}) => {
  const answeredCount = Object.values(answers).filter((a) => a !== null).length;
  const totalCount = questions.length;
  const currentIdx = questions.findIndex((q) => q.id === currentQuestionId);
  const currentMarkedVal = answers[currentQuestionId] || null;

  return (
    <div className="omr-container">
      {/* OMR 헤더 */}
      <div className="omr-header">
        <div className="omr-header-title">
          <ClipboardCheck size={18} className="text-secondary" />
          <span className="omr-title">OMR 실시간 마킹판</span>
        </div>
        {!isReviewMode && (
          <span className="omr-status">
            <strong>{answeredCount}</strong> / {totalCount} 완료
          </span>
        )}
      </div>

      {/* 1. 컴팩트 OMR 그리드 보드 (1~50 한눈에 확인 가능) */}
      <div className="omr-grid-dashboard">
        {questions.map((q, idx) => {
          const markedVal = answers[q.id] || null;
          const isCurrent = q.id === currentQuestionId;
          
          let gridItemClass = "omr-grid-item";
          if (isCurrent) gridItemClass += " active";

          if (isReviewMode) {
            const isCorrect = q.answer === 0 || markedVal === q.answer;
            gridItemClass += isCorrect ? " correct" : " incorrect";
          } else {
            if (markedVal !== null) {
              gridItemClass += " marked";
            }
          }

          return (
            <button
              key={q.id}
              type="button"
              onClick={() => onJumpToQuestion(idx)}
              className={gridItemClass}
              title={`${q.id}번 문제로 바로 이동 (마킹: ${markedVal || "없음"})`}
            >
              <span className="q-num-label">{q.id}</span>
              {markedVal !== null && !isReviewMode && (
                <span className="q-marked-val">{markedVal}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* 2. 현재 활성화된 질문의 상세 5지선다 OMR 마킹 라인 */}
      <div className="omr-current-marking-panel">
        <div className="current-marking-header">
          <CornerDownRight size={14} className="info-icon" />
          <span>현재 <strong>Q{currentQuestionId}</strong>번 마킹</span>
        </div>
        <div className="current-omr-row">
          {[1, 2, 3, 4, 5].map((num) => {
            const isBubbleSelected = currentMarkedVal === num;
            
            let bubbleClass = "omr-bubble-large";
            if (isReviewMode) {
              const isRealAnswer = questions[currentIdx]?.answer === num;
              if (isRealAnswer) {
                bubbleClass += " bubble-correct-ans"; // 실제 정답 표시
              }
              if (isBubbleSelected) {
                const isCorrect = questions[currentIdx]?.answer === 0 || currentMarkedVal === questions[currentIdx]?.answer;
                bubbleClass += isCorrect ? " bubble-marked-correct" : " bubble-marked-incorrect";
              }
            } else {
              if (isBubbleSelected) {
                bubbleClass += " bubble-selected";
              }
            }

            return (
              <button
                key={num}
                type="button"
                disabled={isReviewMode}
                onClick={() => onMarkAnswer(currentQuestionId, num)}
                className={bubbleClass}
              >
                {num}
              </button>
            );
          })}
        </div>
      </div>

      {/* OMR 범례 / 제출 컨트롤 영역 */}
      {!isReviewMode ? (
        <button
          onClick={onSubmit}
          className="omr-submit-btn"
        >
          <Check size={16} />
          <span>답안 최종 제출하기</span>
        </button>
      ) : (
        <div className="omr-review-info">
          <div className="review-legend">
            <span className="legend-item">
              <span className="legend-dot correct"></span> 맞음
            </span>
            <span className="legend-item">
              <span className="legend-dot incorrect"></span> 틀림
            </span>
            <span className="legend-item">
              <span className="legend-dot actual"></span> 정답번호
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
