import React from "react";
import { Award, RotateCcw, BookOpen, Clock, AlertCircle, ThumbsUp, ThumbsDown } from "lucide-react";

interface Question {
  id: number;
  epoch: string;
  score: number;
  question: string;
  answer: number;
  explanation: string;
}

interface ResultDashboardProps {
  questions: Question[];
  answers: Record<number, number | null>;
  elapsedSeconds: number;
  onRestart: () => void;
  onStartReview: () => void;
  onViewSummary: () => void;
}

export const ResultDashboard: React.FC<ResultDashboardProps> = ({
  questions,
  answers,
  elapsedSeconds,
  onRestart,
  onStartReview,
  onViewSummary,
}) => {
  // 점수 계산
  const totalScoreLimit = questions.reduce((sum, q) => sum + q.score, 0);
  const earnedScore = questions.reduce((sum, q) => {
    return sum + (answers[q.id] === q.answer ? q.score : 0);
  }, 0);

  const percentageScore = Math.round((earnedScore / totalScoreLimit) * 100);

  // 등급 판정
  let passGrade = "불합격";
  let gradeClass = "grade-fail";
  let gradeIcon = <ThumbsDown size={40} />;
  let feedbackMessage = "아쉽습니다! 기출 개념 정리를 다시 한 번 꼼꼼히 학습해 보세요.";

  if (percentageScore >= 80) {
    passGrade = "1급 (1등급)";
    gradeClass = "grade-1";
    gradeIcon = <Award size={40} className="shine" />;
    feedbackMessage = "축하합니다! 최고 등급인 1급(1등급)에 합격하셨습니다! 실전에서도 고득점이 기대됩니다.";
  } else if (percentageScore >= 70) {
    passGrade = "2급 (2등급)";
    gradeClass = "grade-2";
    gradeIcon = <Award size={40} />;
    feedbackMessage = "우수합니다! 2급(2등급)에 합격하셨습니다. 조금만 더 빈출 오답을 다듬으면 1급도 가능해요!";
  } else if (percentageScore >= 60) {
    passGrade = "3급 (3등급)";
    gradeClass = "grade-3";
    gradeIcon = <ThumbsUp size={40} />;
    feedbackMessage = "통과했습니다! 3급(3등급)에 합격하셨습니다. 오답 노트를 통해 취약한 시대를 보강해 보세요.";
  }

  // 시대별 통계 분석
  const epochStats: Record<string, { total: number; correct: number }> = {};
  questions.forEach((q) => {
    if (!epochStats[q.epoch]) {
      epochStats[q.epoch] = { total: 0, correct: 0 };
    }
    epochStats[q.epoch].total += 1;
    if (answers[q.id] === q.answer) {
      epochStats[q.epoch].correct += 1;
    }
  });

  const formatTime = (totalSecs: number) => {
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins}분 ${secs}초`;
  };

  const incorrectQuestions = questions.filter((q) => answers[q.id] !== q.answer);

  return (
    <div className="dashboard-container fade-in">
      <h2 className="dashboard-title">시험 결과 대시보드</h2>

      {/* 결과 요약 카드 */}
      <div className="result-summary-card">
        <div className={`grade-badge-large ${gradeClass}`}>
          {gradeIcon}
          <span className="grade-text">{passGrade}</span>
        </div>
        <div className="stats-main">
          <div className="stat-score">
            <span className="score-num">{percentageScore}</span>
            <span className="score-unit">점 / 100점 환산</span>
          </div>
          <div className="stat-details">
            <div className="stat-item">
              <Clock size={16} />
              <span>풀이 시간: <strong>{formatTime(elapsedSeconds)}</strong></span>
            </div>
            <div className="stat-item">
              <AlertCircle size={16} />
              <span>맞힌 문항: <strong>{questions.length - incorrectQuestions.length}개</strong> / {questions.length}개</span>
            </div>
          </div>
        </div>
        
        {/* 한능검 심화 공식 합격 등급 기준표 */}
        <div className="grading-criteria-panel">
          <h4>📋 한능검 심화 등급 합격 기준</h4>
          <div className="criteria-table">
            <div className="criteria-col active-1">
              <span className="c-grade">1급 (1등급)</span>
              <span className="c-score">80점 이상</span>
            </div>
            <div className="criteria-col active-2">
              <span className="c-grade">2급 (2등급)</span>
              <span className="c-score">70점 ~ 79점</span>
            </div>
            <div className="criteria-col active-3">
              <span className="c-grade">3급 (3등급)</span>
              <span className="c-score">60점 ~ 69점</span>
            </div>
            <div className="criteria-col">
              <span className="c-grade text-muted">불합격</span>
              <span className="c-score text-muted">60점 미만</span>
            </div>
          </div>
        </div>

        <p className="feedback-message">{feedbackMessage}</p>
      </div>

      {/* 오답 및 통계 레이아웃 */}
      <div className="dashboard-grid">
        {/* 시대별 약점 분석 (SVG Bar 차트 형식) */}
        <div className="dashboard-card analysis-card">
          <h3>📊 시대별 정답률 & 약점 분석</h3>
          <div className="epoch-bars-container">
            {Object.entries(epochStats).map(([epoch, stat]) => {
              const accuracy = Math.round((stat.correct / stat.total) * 100);
              let barColor = "var(--success-color)";
              if (accuracy < 50) barColor = "var(--danger-color)";
              else if (accuracy < 80) barColor = "var(--warning-color)";

              return (
                <div key={epoch} className="epoch-bar-row">
                  <div className="epoch-bar-label">
                    <span className="epoch-name">{epoch}</span>
                    <span className="epoch-ratio">({stat.correct}/{stat.total} 문항)</span>
                  </div>
                  <div className="epoch-bar-outer">
                    <div
                      className="epoch-bar-inner"
                      style={{
                        width: `${accuracy}%`,
                        backgroundColor: barColor,
                      }}
                    ></div>
                    <span className="accuracy-label">{accuracy}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 오답 키워드 리스트 */}
        <div className="dashboard-card incorrect-card">
          <h3>📌 오답 취약 개념 리스트</h3>
          {incorrectQuestions.length === 0 ? (
            <div className="all-correct-box">
              <ThumbsUp size={32} className="text-success" />
              <p>틀린 문제가 없습니다! 완벽한 실력입니다.</p>
            </div>
          ) : (
            <div className="incorrect-list">
              {incorrectQuestions.map((q) => (
                <div key={q.id} className="incorrect-item-summary">
                  <div className="incorrect-item-header">
                    <span className="incorrect-num-badge">Q{q.id}</span>
                    <span className="incorrect-epoch-badge">{q.epoch}</span>
                  </div>
                  <p className="incorrect-q-title">{q.question}</p>
                  <div className="incorrect-my-answer">
                    내가 마킹한 번호: <strong className="text-danger">{answers[q.id] || "미마킹"}</strong> | 
                    실제 정답: <strong className="text-success">{q.answer}번</strong>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 컨트롤 영역 */}
      <div className="dashboard-actions">
        <button onClick={onRestart} className="btn btn-secondary">
          <RotateCcw size={16} />
          <span>다시 응시하기</span>
        </button>
        <button onClick={onStartReview} className="btn btn-primary" disabled={incorrectQuestions.length === 0}>
          <BookOpen size={16} />
          <span>오답 노트 공부하기</span>
        </button>
        <button onClick={onViewSummary} className="btn btn-info">
          <BookOpen size={16} />
          <span>시대별 핵심 요약집</span>
        </button>
      </div>
    </div>
  );
};
