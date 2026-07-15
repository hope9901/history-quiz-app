import { Check, ClipboardCheck } from "lucide-react";

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

  return (
    <div className="omr-container">
      <div className="omr-header">
        <ClipboardCheck size={18} />
        <span className="omr-title">OMR 답안지</span>
        {!isReviewMode && (
          <span className="omr-status">
            {answeredCount}/{totalCount} 마킹완료
          </span>
        )}
      </div>

      <div className="omr-grid">
        {questions.map((q, idx) => {
          const markedVal = answers[q.id] || null;
          const isCurrent = q.id === currentQuestionId;
          const isCorrect = markedVal === q.answer;

          return (
            <div
              key={q.id}
              className={`omr-row ${isCurrent ? "omr-row-current" : ""}`}
            >
              {/* 문제 인덱스 번호 및 점프 버튼 */}
              <button
                type="button"
                onClick={() => onJumpToQuestion(idx)}
                className={`omr-num-btn ${
                  isReviewMode
                    ? isCorrect
                      ? "omr-num-correct"
                      : "omr-num-incorrect"
                    : markedVal !== null
                    ? "omr-num-marked"
                    : ""
                }`}
                title={`${q.id}번 문제로 이동`}
              >
                {q.id}
              </button>

              {/* 1번부터 5번까지의 마킹 버블 */}
              <div className="omr-bubbles">
                {[1, 2, 3, 4, 5].map((num) => {
                  const isBubbleSelected = markedVal === num;
                  const isRealAnswer = q.answer === num;
                  
                  let bubbleClass = "omr-bubble";
                  if (isReviewMode) {
                    if (isRealAnswer) {
                      bubbleClass += " bubble-correct-ans"; // 실제 정답 표시
                    }
                    if (isBubbleSelected) {
                      if (isCorrect) {
                        bubbleClass += " bubble-marked-correct";
                      } else {
                        bubbleClass += " bubble-marked-incorrect";
                      }
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
                      onClick={() => onMarkAnswer(q.id, num)}
                      className={bubbleClass}
                    >
                      {num}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* 최종 제출 / 작업 완료 버튼 */}
      {!isReviewMode ? (
        <button
          onClick={onSubmit}
          className="omr-submit-btn"
        >
          <Check size={16} />
          <span>답안 최종 제출</span>
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
