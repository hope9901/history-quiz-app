import React, { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, CheckCircle2, XCircle, Info, ZoomIn } from "lucide-react";
import { ImageLightbox } from "./ImageLightbox";

interface Question {
  id: number;
  epoch: string;
  score: number;
  question: string;
  material: string;
  imageUrl?: string; // 이미지 속성 추가
  options: string[];
  answer: number;
  explanation: string;
  summaryNote: string;
}

interface QuestionCardProps {
  question: Question;
  currentIndex: number;
  totalQuestions: number;
  selectedAnswer: number | null;
  onSelectOption: (questionId: number, optionIndex: number) => void;
  onPrev: () => void;
  onNext: () => void;
  isReviewMode?: boolean;
}

export const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  currentIndex,
  totalQuestions,
  selectedAnswer,
  onSelectOption,
  onPrev,
  onNext,
  isReviewMode = false,
}) => {
  const [imageError, setImageError] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);

  // 문제 번호가 변경될 때마다 이미지 에러/확대 상태 초기화
  useEffect(() => {
    setImageError(false);
    setZoomOpen(false);
  }, [question.id]);

  return (
    <div className={`question-card-container ${isReviewMode ? "review-mode" : ""}`}>
      {/* 문제 헤더 */}
      <div className="question-card-header">
        <div className="question-badge-group">
          <span className="epoch-badge">{question.epoch}</span>
          <span className="score-badge">{question.score}점</span>
        </div>
        <span className="question-progress">
          {currentIndex + 1} / {totalQuestions}
        </span>
      </div>

      {/* 문제 본문 */}
      <h3 className="question-title">
        <span className="q-number">Q{question.id}.</span> {question.question}
      </h3>

      {/* 사료 자료 박스 */}
      {question.material && (
        <div className="material-box">
          <p className="material-text">{question.material}</p>
        </div>
      )}

      {/* 시각 자료 이미지 박스 (깨짐 방지 폴백 탑재) */}
      {question.imageUrl && !imageError ? (
        <div className="material-image-box animate-fade-in">
          <img
            src={question.imageUrl}
            alt="문제 지문"
            className="question-material-image zoomable"
            onClick={() => setZoomOpen(true)}
            onError={() => setImageError(true)}
          />
          <button className="zoom-hint-btn" onClick={() => setZoomOpen(true)}>
            <ZoomIn size={14} />
            <span>글자가 작으면 눌러서 확대</span>
          </button>
          {zoomOpen && (
            <ImageLightbox src={question.imageUrl} alt="문제 지문 확대" onClose={() => setZoomOpen(false)} />
          )}
        </div>
      ) : question.imageUrl && imageError ? (
        <div className="material-image-placeholder">
          🖼️ 시각 자료 [ 이미지 로드 실패: {question.epoch} 관련 유물 자료 ]
        </div>
      ) : null}

      {/* 보기 선택지 - 가로 한 줄 버블 레이아웃 개편 */}
      <div className="options-horizontal-container">
        <span className="marking-label">답안 선택:</span>
        <div className="options-horizontal-row">
          {[1, 2, 3, 4, 5].map((num) => {
            const isSelected = selectedAnswer === num;
            const isCorrectAnswer = question.answer === num;
            
            let btnClass = "option-bubble-btn";
            if (isReviewMode) {
              if (isCorrectAnswer) {
                btnClass += " correct";
              } else if (isSelected && !isCorrectAnswer) {
                btnClass += " incorrect";
              } else {
                btnClass += " disabled";
              }
            } else {
              if (isSelected) {
                btnClass += " selected";
              }
            }

            return (
              <button
                key={num}
                disabled={isReviewMode}
                onClick={() => onSelectOption(question.id, num)}
                className={btnClass}
              >
                {isReviewMode && isCorrectAnswer ? (
                  <CheckCircle2 size={16} className="text-success" />
                ) : isReviewMode && isSelected && !isCorrectAnswer ? (
                  <XCircle size={16} className="text-danger" />
                ) : (
                  <span className="bubble-val">{num}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* 오답노트 해설 영역 (리뷰 모드에서만 출력) */}
      {isReviewMode && (
        <div className="explanation-section fade-in">
          <div className="explanation-box">
            <h4 className="explanation-title">
              <Info size={16} />
              <span>정답 해설 ({question.answer}번)</span>
            </h4>
            <p className="explanation-text">{question.explanation}</p>
          </div>
          <div className="summary-note-box">
            <h4 className="summary-title">📘 핵심 개념 정리</h4>
            <p className="summary-text">{question.summaryNote}</p>
          </div>
        </div>
      )}

      {/* 하단 네비게이션 컨트롤 */}
      <div className="question-navigation">
        <button
          onClick={onPrev}
          disabled={currentIndex === 0}
          className="nav-btn"
        >
          <ChevronLeft size={18} />
          <span>이전 문제</span>
        </button>
        <button
          onClick={onNext}
          disabled={currentIndex === totalQuestions - 1}
          className="nav-btn"
        >
          <span>다음 문제</span>
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
};
