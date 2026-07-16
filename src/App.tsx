import { useState } from "react";
import questionsData from "./data/official_questions.json";
import { ExamTimer } from "./components/ExamTimer";
import { QuestionCard } from "./components/QuestionCard";
import { OMRSheet } from "./components/OMRSheet";
import { ResultDashboard } from "./components/ResultDashboard";
import { SummaryNotes } from "./components/SummaryNotes";
import { WrongAnswerArchive } from "./components/WrongAnswerArchive";
import { GraduationCap, Award, BookOpen, Clock, AlertCircle } from "lucide-react";
import "./App.css";

type TabType = "INTRO" | "EXAM" | "RESULT" | "REVIEW" | "SUMMARY" | "ARCHIVE";

interface Question {
  id: number;
  epoch: string;
  score: number;
  question: string;
  material: string;
  imageUrl?: string; // 이미지 필드 추가
  options: string[];
  answer: number;
  explanation: string;
  summaryNote: string;
}

interface ArchivedQuestion {
  archiveId: string;
  session: string;
  questionId: number;
  epoch: string;
  question: string;
  material: string;
  imageUrl?: string; // 이미지 필드 추가
  options: string[];
  myAnswer: number | null;
  correctAnswer: number;
  explanation: string;
  summaryNote: string;
  timestamp: number;
}

function App() {
  const [activeTab, setActiveTab] = useState<TabType>("INTRO");
  const [selectedSession, setSelectedSession] = useState<string>("76");
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  
  // 현재 선택된 회차의 문제 목록 가져오기
  const questions: Question[] = (questionsData as Record<string, Question[]>)[selectedSession] || [];

  const [answers, setAnswers] = useState<Record<number, number | null>>({});
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isTimerActive, setIsTimerActive] = useState(false);

  // 사용 가능한 모든 시험 회차 키 배열
  const sessions = Object.keys(questionsData);

  // 시험 시작
  const handleStartExam = () => {
    const initialAnswers: Record<number, number | null> = {};
    questions.forEach((q) => {
      initialAnswers[q.id] = null;
    });
    setAnswers(initialAnswers);
    setCurrentQuestionIndex(0);
    setElapsedSeconds(0);
    setIsTimerActive(true);
    setActiveTab("EXAM");
  };

  // 답안 선택 (문제 카드)
  const handleSelectOption = (questionId: number, optionIndex: number) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: optionIndex,
    }));
  };

  // 마킹 버블 선택 (OMR 시트)
  const handleMarkAnswer = (questionId: number, answerNum: number) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: answerNum,
    }));
  };

  // 특정 문제로 직접 점프
  const handleJumpToQuestion = (index: number) => {
    setCurrentQuestionIndex(index);
  };

  // 타이머 시간 업데이트
  const handleTimeUpdate = (elapsed: number) => {
    setElapsedSeconds(elapsed);
  };

  // 오답 데이터 로컬 스토리지 자동 저장 함수
  const archiveWrongAnswers = () => {
    const timestamp = Date.now();
    const wrongList: ArchivedQuestion[] = [];

    questions.forEach((q) => {
      const myAns = answers[q.id] || null;
      if (myAns !== q.answer) {
        wrongList.push({
          archiveId: `${selectedSession}_${q.id}_${timestamp}`,
          session: selectedSession,
          questionId: q.id,
          epoch: q.epoch,
          question: q.question,
          material: q.material,
          imageUrl: q.imageUrl || "", // 이미지 필드 이식
          options: q.options,
          myAnswer: myAns,
          correctAnswer: q.answer,
          explanation: q.explanation,
          summaryNote: q.summaryNote,
          timestamp: timestamp
        });
      }
    });

    if (wrongList.length === 0) return;

    // 기존 오답 로드 및 병합 (중복 방지)
    const existing = localStorage.getItem("history_exam_notes");
    let combined: ArchivedQuestion[] = [];
    
    if (existing) {
      try {
        const parsed = JSON.parse(existing) as ArchivedQuestion[];
        // 동일 회차의 동일 문제 번호가 이미 존재한다면 중복 적재를 막기 위해 제거 후 신규 추가
        const filtered = parsed.filter(
          (item) => !(item.session === selectedSession && wrongList.some(w => w.questionId === item.questionId))
        );
        combined = [...filtered, ...wrongList];
      } catch (e) {
        combined = wrongList;
      }
    } else {
      combined = wrongList;
    }

    localStorage.setItem("history_exam_notes", JSON.stringify(combined));
  };

  // 최종 답안 제출
  const handleSubmitExam = () => {
    const unansweredCount = questions.filter((q) => answers[q.id] === null).length;
    
    if (unansweredCount > 0) {
      const confirmSubmit = window.confirm(
        `아직 마킹하지 않은 문제가 ${unansweredCount}개 있습니다. 정말로 제출하시겠습니까?`
      );
      if (!confirmSubmit) return;
    }

    setIsTimerActive(false);
    archiveWrongAnswers(); // 오답 저장 실행
    setActiveTab("RESULT");
  };

  // 타이머 타임아웃 종료
  const handleTimeOver = () => {
    alert("제한 시간이 초과되었습니다! 답안이 자동으로 제출되고 오답이 보관됩니다.");
    setIsTimerActive(false);
    archiveWrongAnswers(); // 오답 저장 실행
    setActiveTab("RESULT");
  };

  // 오답노트 공부하기 시작
  const handleStartReview = () => {
    // 첫 오답 찾아서 거기로 인덱스 맞춰둠
    const firstWrongIdx = questions.findIndex(
      (q) => answers[q.id] !== q.answer
    );
    setCurrentQuestionIndex(firstWrongIdx !== -1 ? firstWrongIdx : 0);
    setActiveTab("REVIEW");
  };

  // 이전/다음 문제 네비게이션
  const handlePrevQuestion = () => {
    setCurrentQuestionIndex((prev) => Math.max(0, prev - 1));
  };

  const handleNextQuestion = () => {
    setCurrentQuestionIndex((prev) => Math.min(questions.length - 1, prev + 1));
  };

  const currentQuestion = questions[currentQuestionIndex] || null;

  return (
    <div className="app-container">
      {/* 글로벌 헤더 */}
      <header className="app-header">
        <div className="header-logo" onClick={() => setActiveTab("INTRO")}>
          <GraduationCap className="logo-icon" size={28} />
          <h1>한능검 Master</h1>
        </div>
        <nav className="header-nav">
          <button
            onClick={() => {
              if (activeTab === "EXAM" && !window.confirm("시험을 중단하시겠습니까? 풀이 기록이 사라집니다.")) return;
              setIsTimerActive(false);
              setActiveTab("INTRO");
            }}
            className={`nav-link ${activeTab === "INTRO" ? "active" : ""}`}
          >
            홈
          </button>
          <button
            onClick={() => {
              if (activeTab === "EXAM" && !window.confirm("시험을 중단하시겠습니까? 풀이 기록이 사라집니다.")) return;
              setIsTimerActive(false);
              setActiveTab("SUMMARY");
            }}
            className={`nav-link ${activeTab === "SUMMARY" ? "active" : ""}`}
          >
            시대별 요약
          </button>
          <button
            onClick={() => {
              if (activeTab === "EXAM" && !window.confirm("시험을 중단하시겠습니까? 풀이 기록이 사라집니다.")) return;
              setIsTimerActive(false);
              setActiveTab("ARCHIVE");
            }}
            className={`nav-link ${activeTab === "ARCHIVE" ? "active" : ""}`}
          >
            오답 보관함
          </button>
        </nav>
      </header>

      {/* 메인 콘텐츠 바디 */}
      <main className="app-main-content">
        {activeTab === "INTRO" && (
          <div className="intro-container fade-in">
            <div className="intro-hero-section">
              <Award className="hero-icon animated-float" size={64} />
              <h2>한국사능력검정시험 실전 모의고사 & 오답노트</h2>
              <p className="hero-subtitle">
                실제 시험과 동일한 **80분 제한시간** 동안 문제를 풀고,<br />
                틀린 개념들은 오답 보관함에 누적 보관하여 완벽히 정복하세요. (노션 비연동 로컬 보관)
              </p>
            </div>

            {/* 회차 선택 셀렉트 박스 */}
            <div className="session-select-card">
              <h3>📅 모의고사 응시 회차 선택</h3>
              <div className="session-select-row">
                <select
                  value={selectedSession}
                  onChange={(e) => setSelectedSession(e.target.value)}
                  className="session-select-dropdown"
                >
                  {sessions.map((sess) => (
                    <option key={sess} value={sess}>
                      제{sess}회 한국사능력검정시험 기출 (심화)
                    </option>
                  ))}
                </select>
                <span className="question-count-info">총 {questions.length}문항 수록</span>
              </div>
            </div>

            <div className="intro-features-grid">
              <div className="feature-card">
                <Clock className="feature-icon" size={24} />
                <h3>실전 타이머 (80분)</h3>
                <p>실제 시험과 동일한 시간 기준이 제공되며 OMR 시트로 최종 답안을 제출합니다.</p>
              </div>
              <div className="feature-card">
                <BookOpen className="feature-icon" size={24} />
                <h3>오답 자동 아카이빙</h3>
                <p>제출 후 틀린 문제는 [오답 보관함] 탭으로 자동 백업되어 평생 저장됩니다.</p>
              </div>
              <div className="feature-card">
                <AlertCircle className="feature-icon" size={24} />
                <h3>마스터 완료 시스템</h3>
                <p>보관함에 쌓인 오답을 확인하고, 개념을 완벽하게 외우면 마스터(삭제) 처리합니다.</p>
              </div>
            </div>

            <div className="intro-start-section">
              <button onClick={handleStartExam} className="start-btn-primary">
                실전 모의고사 시작
              </button>
              <button onClick={() => setActiveTab("ARCHIVE")} className="start-btn-secondary">
                내 오답 보관함 가기
              </button>
            </div>
          </div>
        )}

        {/* 시험 진행 화면 */}
        {activeTab === "EXAM" && currentQuestion && (
          <div className="exam-layout fade-in">
            {/* 좌측: 문제 풀이 영역 */}
            <div className="exam-workspace">
              <QuestionCard
                question={currentQuestion}
                currentIndex={currentQuestionIndex}
                totalQuestions={questions.length}
                selectedAnswer={answers[currentQuestion.id] || null}
                onSelectOption={handleSelectOption}
                onPrev={handlePrevQuestion}
                onNext={handleNextQuestion}
              />
            </div>
            
            {/* 우측: 시간 & OMR 마킹 시트 */}
            <aside className="exam-sidebar">
              <ExamTimer
                initialSeconds={4800} // 80분 고정
                isActive={isTimerActive}
                onTimeOver={handleTimeOver}
                onTimeUpdate={handleTimeUpdate}
              />
              <OMRSheet
                questions={questions}
                answers={answers}
                currentQuestionId={currentQuestion.id}
                onJumpToQuestion={handleJumpToQuestion}
                onMarkAnswer={handleMarkAnswer}
                onSubmit={handleSubmitExam}
              />
            </aside>
          </div>
        )}

        {/* 결과 대시보드 화면 */}
        {activeTab === "RESULT" && (
          <ResultDashboard
            questions={questions}
            answers={answers}
            elapsedSeconds={elapsedSeconds}
            onRestart={handleStartExam}
            onStartReview={handleStartReview}
            onViewSummary={() => setActiveTab("SUMMARY")}
          />
        )}

        {/* 오답노트 복습 화면 */}
        {activeTab === "REVIEW" && currentQuestion && (
          <div className="exam-layout fade-in">
            {/* 좌측: 문제 및 해설, 개념요약 */}
            <div className="exam-workspace">
              <QuestionCard
                question={currentQuestion}
                currentIndex={currentQuestionIndex}
                totalQuestions={questions.length}
                selectedAnswer={answers[currentQuestion.id] || null}
                onSelectOption={handleSelectOption}
                onPrev={handlePrevQuestion}
                onNext={handleNextQuestion}
                isReviewMode={true}
              />
            </div>
            
            {/* 우측: 오답 OMR 마킹 시트 (결과 확인용) */}
            <aside className="exam-sidebar">
              <div className="review-exit-card">
                <h3>오답 복습 중</h3>
                <p>오답 오리엔테이션을 보며 취약점 분석 및 개념을 학습해보세요.</p>
                <button
                  onClick={() => setActiveTab("RESULT")}
                  className="btn btn-primary"
                  style={{ width: "100%" }}
                >
                  결과 화면으로 돌아가기
                </button>
              </div>
              <OMRSheet
                questions={questions}
                answers={answers}
                currentQuestionId={currentQuestion.id}
                onJumpToQuestion={handleJumpToQuestion}
                onMarkAnswer={handleMarkAnswer}
                onSubmit={() => {}}
                isReviewMode={true}
              />
            </aside>
          </div>
        )}

        {/* 시대별 핵심 요약집 화면 */}
        {activeTab === "SUMMARY" && (
          <div className="summary-layout">
            <SummaryNotes />
          </div>
        )}

        {/* 로컬 오답 보관함 화면 */}
        {activeTab === "ARCHIVE" && (
          <div className="archive-layout">
            <WrongAnswerArchive />
          </div>
        )}
      </main>

      {/* 글로벌 푸터: 문항 및 이미지 출처 표기 */}
      <footer className="app-footer">
        <p>© 2026 한능검 Master. 개인 학습용 비영리 프로젝트입니다.</p>
        <div className="footer-credits">
          <p className="footer-credit-title">문항 출처</p>
          <p>
            본 서비스의 문항은 국사편찬위원회 주관 한국사능력검정시험 제72·75·76·77회(심화)의{" "}
            <a href="https://www.historyexam.go.kr/pst/list.do?bbs=dat" target="_blank" rel="noopener noreferrer">
              공식 홈페이지 시험자료실
            </a>
            에서 공개한 문제지·정답표 원문을 변형 없이 문항 단위 이미지로 수록한 것입니다. 기출문제의
            저작권은 국사편찬위원회에 있으며,{" "}
            <a href="https://www.kogl.or.kr/info/license.do" target="_blank" rel="noopener noreferrer">
              공공누리 제4유형(출처표시·상업적 이용금지·변경금지)
            </a>{" "}
            조건에 따라 비영리 학습 목적으로만 이용합니다. 문항에 사용된 사진 등의 저작권은
            원저작자에게 있습니다.
          </p>
          <p>
            ※ 제73·74·78회는 공개된 문제지가 스캔 이미지 형식이어서 문항 단위 수록이 어려워 제외되었습니다.
            국사편찬위원회는 기출문제 해설을 제공하지 않으므로, 본 서비스의 정답은 공식 정답표를
            따르되 해설은 제공되지 않습니다.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
