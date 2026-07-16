import { useState, useEffect } from "react";
import { BookOpen, CheckCircle, Trash2, Filter, AlertCircle, HelpCircle } from "lucide-react";

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

export const WrongAnswerArchive: React.FC = () => {
  const [archivedList, setArchivedList] = useState<ArchivedQuestion[]>([]);
  const [activeSessionFilter, setActiveSessionFilter] = useState<string>("ALL");
  const [activeEpochFilter, setActiveEpochFilter] = useState<string>("ALL");
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [imageErrors, setImageErrors] = useState<Record<string, boolean>>({});

  // 로컬스토리지에서 오답 데이터 가져오기
  useEffect(() => {
    const loadArchive = () => {
      const data = localStorage.getItem("history_exam_notes");
      if (data) {
        try {
          const parsed = JSON.parse(data) as ArchivedQuestion[];
          // 시간 역순(최신 오답이 위로) 정렬
          const sorted = parsed.sort((a, b) => b.timestamp - a.timestamp);
          setArchivedList(sorted);
        } catch (e) {
          console.error("오답 노트를 로드하는 데 실패했습니다.", e);
        }
      }
    };
    loadArchive();
  }, []);

  // 카드 토글 함수
  const toggleCard = (archiveId: string) => {
    setExpandedCards((prev) => ({
      ...prev,
      [archiveId]: !prev[archiveId],
    }));
  };

  // 오답 카드 삭제 (개념 마스터)
  const handleMasterComplete = (archiveId: string) => {
    const updated = archivedList.filter((item) => item.archiveId !== archiveId);
    setArchivedList(updated);
    localStorage.setItem("history_exam_notes", JSON.stringify(updated));
  };

  // 모든 오답 일괄 삭제
  const handleClearAll = () => {
    if (window.confirm("정말로 모든 오답 기록을 삭제하시겠습니까? 복구할 수 없습니다.")) {
      setArchivedList([]);
      localStorage.removeItem("history_exam_notes");
    }
  };

  // 필터링 적용된 목록 계산
  const filteredList = archivedList.filter((item) => {
    const matchSession = activeSessionFilter === "ALL" || item.session === activeSessionFilter;
    const matchEpoch = activeEpochFilter === "ALL" || item.epoch === activeEpochFilter;
    return matchSession && matchEpoch;
  });

  // 고유한 회차 및 시대 목록 추출 (필터 칩 생성용)
  const sessions = ["ALL", ...Array.from(new Set(archivedList.map((item) => item.session)))];
  const epochs = ["ALL", ...Array.from(new Set(archivedList.map((item) => item.epoch)))];

  const formatDate = (ts: number) => {
    const date = new Date(ts);
    return `${date.getFullYear()}.${(date.getMonth() + 1).toString().padStart(2, "0")}.${date.getDate().toString().padStart(2, "0")}`;
  };

  return (
    <div className="archive-view-container fade-in">
      <div className="archive-view-header">
        <div className="archive-header-title">
          <BookOpen size={24} className="text-secondary" />
          <h2>로컬 오답 보관함</h2>
          <span className="archive-count-badge">{archivedList.length}개 보관 중</span>
        </div>
        {archivedList.length > 0 && (
          <button onClick={handleClearAll} className="btn-clear-all" title="보관함 비우기">
            <Trash2 size={15} />
            <span>보관함 비우기</span>
          </button>
        )}
      </div>

      {archivedList.length === 0 ? (
        <div className="archive-empty-state">
          <CheckCircle size={64} className="empty-icon pulse" />
          <h3>보관된 오답이 없습니다!</h3>
          <p>모의고사를 제출하면 틀린 문제들이 자동으로 이곳에 보관됩니다.</p>
        </div>
      ) : (
        <>
          {/* 다중 필터 제어 영역 */}
          <div className="archive-filter-panel">
            <div className="filter-group">
              <span className="filter-label">
                <Filter size={14} />
                <span>회차별 필터</span>
              </span>
              <div className="filter-chips">
                {sessions.map((sess) => (
                  <button
                    key={sess}
                    onClick={() => setActiveSessionFilter(sess)}
                    className={`filter-chip ${activeSessionFilter === sess ? "active" : ""}`}
                  >
                    {sess === "ALL" ? "전체 회차" : `제${sess}회`}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-group">
              <span className="filter-label">
                <Filter size={14} />
                <span>시대별 필터</span>
              </span>
              <div className="filter-chips">
                {epochs.map((ep) => (
                  <button
                    key={ep}
                    onClick={() => setActiveEpochFilter(ep)}
                    className={`filter-chip ${activeEpochFilter === ep ? "active" : ""}`}
                  >
                    {ep === "ALL" ? "전체 시대" : ep}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 오답 카드 리스트 그리드 */}
          {filteredList.length === 0 ? (
            <div className="archive-no-results">
              <AlertCircle size={32} className="text-muted" />
              <p>해당 필터 조건에 부합하는 오답 카드가 없습니다.</p>
            </div>
          ) : (
            <div className="archive-grid">
              {filteredList.map((item) => {
                const isExpanded = !!expandedCards[item.archiveId];
                const hasError = !!imageErrors[item.archiveId];
                return (
                  <div
                    key={item.archiveId}
                    className={`archive-card ${isExpanded ? "expanded" : ""}`}
                  >
                    {/* 카드 메인 상단 요약 바 */}
                    <div className="archive-card-summary" onClick={() => toggleCard(item.archiveId)}>
                      <div className="summary-badges">
                        <span className="badge-sess">제{item.session}회</span>
                        <span className="badge-qnum">Q{item.questionId}</span>
                        <span className="badge-epoch">{item.epoch}</span>
                      </div>
                      <h4 className="summary-title-text">{item.question}</h4>
                      <div className="summary-right">
                        <span className="summary-date">{formatDate(item.timestamp)}</span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation(); // 카드 토글 방지
                            handleMasterComplete(item.archiveId);
                          }}
                          className="btn-master-complete"
                          title="마스터 완료 (삭제)"
                        >
                          <CheckCircle size={14} />
                          <span>마스터</span>
                        </button>
                      </div>
                    </div>

                    {/* 카드 확장 콘텐츠 영역 */}
                    {isExpanded && (
                      <div className="archive-card-content fade-in">
                        {/* 사료 지문 */}
                        {item.material && (
                          <div className="material-box">
                            <p className="material-text">{item.material}</p>
                          </div>
                        )}

                        {/* 시각 자료 이미지 박스 */}
                        {item.imageUrl && !hasError ? (
                          <div className="material-image-box">
                            <img
                              src={item.imageUrl}
                              alt="문제 유물 자료"
                              className="question-material-image"
                              onError={() => setImageErrors((prev) => ({ ...prev, [item.archiveId]: true }))}
                            />
                          </div>
                        ) : item.imageUrl && hasError ? (
                          <div className="material-image-placeholder">
                            🖼️ 시각 자료 [ 이미지 로드 실패: {item.epoch} 관련 유물 자료 ]
                          </div>
                        ) : null}

                        {/* 보기 구성 */}
                        <div className="archive-options-list">
                          {item.options.map((opt, idx) => {
                            const optNum = idx + 1;
                            const isCorrect = item.correctAnswer === optNum;
                            const isMySelection = item.myAnswer === optNum;

                            let optClass = "archive-option-item";
                            if (isCorrect) optClass += " correct";
                            else if (isMySelection) optClass += " incorrect";
                            else optClass += " disabled";

                            return (
                              <div key={idx} className={optClass}>
                                <span className="opt-bubble">{optNum}</span>
                                <span className="opt-text">{opt.substring(3)}</span>
                                {isCorrect && <span className="opt-badge correct-badge">정답</span>}
                                {isMySelection && !isCorrect && (
                                  <span className="opt-badge incorrect-badge">내가 작성한 오답</span>
                                )}
                              </div>
                            );
                          })}
                        </div>

                        {/* 해설 및 요약노트 */}
                        <div className="archive-study-zone">
                          <div className="explanation-box">
                            <h5 className="title-ex">
                              <HelpCircle size={14} />
                              <span>정답 해설</span>
                            </h5>
                            <p className="text-ex">{item.explanation}</p>
                          </div>
                          
                          <div className="summary-note-box">
                            <h5 className="title-sm">📘 시대 핵심 개념</h5>
                            <p className="text-sm">{item.summaryNote}</p>
                          </div>

                          {/* 외부 해설 바로가기 (공식 해설 미제공) */}
                          <div className="external-solutions-box">
                            <span>
                              🔎 제{item.session}회 {item.questionId}번 상세 해설 찾기:{" "}
                              <a
                                href={`https://www.comcbt.com/xe/k1`}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                전자문제집 CBT
                              </a>
                              {" · "}
                              <a
                                href="https://www.ebs.co.kr/pass/examination/history/infomation/problem"
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                EBS 한국사능력시험
                              </a>
                              {" · "}
                              <a
                                href={`https://www.google.com/search?q=${encodeURIComponent(`한국사능력검정시험 ${item.session}회 심화 ${item.questionId}번 해설`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                구글 검색
                              </a>
                            </span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
};
