import React, { useEffect, useState, useRef } from "react";
import { Timer, Play, Pause, AlertTriangle } from "lucide-react";

interface ExamTimerProps {
  initialSeconds: number; // 80분 = 4800초
  isActive: boolean;
  onTimeOver: () => void;
  onTimeUpdate: (elapsedSeconds: number) => void;
}

export const ExamTimer: React.FC<ExamTimerProps> = ({
  initialSeconds,
  isActive,
  onTimeOver,
  onTimeUpdate,
}) => {
  const [timeLeft, setTimeLeft] = useState(initialSeconds);
  const [isPaused, setIsPaused] = useState(!isActive);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    setTimeLeft(initialSeconds);
  }, [initialSeconds]);

  useEffect(() => {
    if (isActive && !isPaused) {
      timerRef.current = window.setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            if (timerRef.current) window.clearInterval(timerRef.current);
            onTimeOver();
            return 0;
          }
          const nextVal = prev - 1;
          onTimeUpdate(initialSeconds - nextVal);
          return nextVal;
        });
      }, 1000);
    } else {
      if (timerRef.current) window.clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [isActive, isPaused, onTimeOver, onTimeUpdate, initialSeconds]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const getTimerStatusClass = () => {
    if (timeLeft <= 180) return "timer-danger pulse"; // 3분 이하
    if (timeLeft <= 600) return "timer-warning"; // 10분 이하
    return "timer-normal";
  };

  return (
    <div className={`timer-container ${getTimerStatusClass()}`}>
      <div className="timer-header">
        <Timer className="timer-icon" size={20} />
        <span className="timer-title">남은 시간</span>
      </div>
      <div className="timer-display">
        {formatTime(timeLeft)}
      </div>
      
      {timeLeft <= 600 && timeLeft > 0 && (
        <div className="timer-alert">
          <AlertTriangle size={14} />
          <span>{timeLeft <= 180 ? "시험 종료 임박!" : "시간이 얼마 남지 않았습니다!"}</span>
        </div>
      )}

      <button
        onClick={() => setIsPaused(!isPaused)}
        className="timer-control-btn"
        title={isPaused ? "타이머 시작" : "타이머 일시정지"}
      >
        {isPaused ? <Play size={16} /> : <Pause size={16} />}
        <span>{isPaused ? "재개" : "일시정지"}</span>
      </button>
    </div>
  );
};
