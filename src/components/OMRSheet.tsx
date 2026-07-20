import React from "react";
import { ClipboardCheck } from "lucide-react";

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
  onSubmit,
  isReviewMode = false,
}) => {
  const answeredCount = Object.values(answers).filter((a) => a !== null).length;
  const totalCount = questions.length;

  return (
    <div className="omr-container">
      {/* OMR 헤더 */}
      <div className="omr-header">
        <div className="omr-header-title">
          <ClipboardCheck size={18} className="text-secondary" />
          <span className="omr-title">OMR 실시간 답안지</span>
        </div>
        {!isReviewMode && (
          <span className="omr-status">
            <strong>{answeredCount}</strong> / {totalCount} 마킹
          </span>
        )}
      </div>

      {/* 세로 일자형 실제 OMR 시트 마킹 테이블 영역 */}
      <div className="omr-vertical-sheet">
        {questions.map((q, idx) => {
          const markedVal = answers[q.id] || null;
          const isCurrent = q.id === currentQuestionId;
          
          let rowClass = "omr-vertical-row";
          if (isCurrent) rowClass += " active";

          if (isReviewMode) {
            const isCorrect = q.answer === 0 || markedVal === q.answer;
            rowClass += isCorrect ? " correct" : " incorrect";
          } else {
            if (markedVal !== null) {
              rowClass += " marked";
            }
          }

          return (
            <div
              key={q.id}
              onClick={() => onJumpToQuestion(idx)}
              className={rowClass}
              title={`${q.id}번 문제로 이동 (현재 마킹: ${markedVal || "없음"})`}
            >
              {/* 맨 왼쪽: 일자로 정렬되는 문제 번호 */}
              <div className="omr-vertical-num">
                <span className="num-prefix">Q</span>
                <span className="num-val">{q.id}</span>
              </div>

              {/* 그 옆: 1~5번 실제 OMR 마킹 동그라미 인디케이터 (클릭해도 답안이 변경되지 않고 보기 전용으로만 작동) */}
              <div className="omr-vertical-bubbles">
                {[1, 2, 3, 4, 5].map((num) => {
                  const isBubbleSelected = markedVal === num;
                  
                  let bubbleClass = "omr-vertical-bubble";
                  if (isReviewMode) {
                    const isRealAnswer = q.answer === num;
                    if (isRealAnswer) {
                      bubbleClass += " correct-answer-point"; // 실제 정답
                    }
                    if (isBubbleSelected) {
                      const isCorrect = q.answer === 0 || markedVal === q.answer;
                      bubbleClass += isCorrect ? " marked-correct" : " marked-incorrect";
                    }
                  } else {
                    if (isBubbleSelected) {
                      bubbleClass += " selected";
                    }
                  }

                  return (
                    <div key={num} className={bubbleClass}>
                      <span className="bubble-num">{num}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* 최종 제출 / 가이드 컨트롤 */}
      {!isReviewMode ? (
        <button
          onClick={onSubmit}
          className="omr-submit-btn"
        >
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
              <span className="legend-dot actual"></span> 정답
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
