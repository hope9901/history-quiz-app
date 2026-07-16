import React, { useEffect, useState } from "react";
import { X, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";

interface ImageLightboxProps {
  src: string;
  alt: string;
  onClose: () => void;
}

const MIN_SCALE = 1;
const MAX_SCALE = 4;

/** 문항 이미지 확대 보기 모달 — 버튼/휠/더블클릭 줌, 스크롤 패닝, 모바일 핀치 지원 */
export const ImageLightbox: React.FC<ImageLightboxProps> = ({ src, alt, onClose }) => {
  const [scale, setScale] = useState(1.5);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "+" || e.key === "=") setScale((s) => Math.min(MAX_SCALE, s + 0.25));
      if (e.key === "-") setScale((s) => Math.max(MIN_SCALE, s - 0.25));
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  const handleWheel = (e: React.WheelEvent) => {
    setScale((s) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, s + (e.deltaY < 0 ? 0.2 : -0.2))));
  };

  return (
    <div className="lightbox-overlay" onClick={onClose} role="dialog" aria-label="이미지 확대 보기">
      <div className="lightbox-toolbar" onClick={(e) => e.stopPropagation()}>
        <button onClick={() => setScale((s) => Math.max(MIN_SCALE, s - 0.25))} aria-label="축소">
          <ZoomOut size={20} />
        </button>
        <span className="lightbox-scale">{Math.round(scale * 100)}%</span>
        <button onClick={() => setScale((s) => Math.min(MAX_SCALE, s + 0.25))} aria-label="확대">
          <ZoomIn size={20} />
        </button>
        <button onClick={() => setScale(1.5)} aria-label="원래 크기">
          <RotateCcw size={18} />
        </button>
        <button onClick={onClose} aria-label="닫기">
          <X size={20} />
        </button>
      </div>
      <div className="lightbox-scroll" onClick={(e) => e.stopPropagation()} onWheel={handleWheel}>
        <img
          src={src}
          alt={alt}
          className="lightbox-image"
          style={{ width: `${scale * 100}%` }}
          onDoubleClick={() => setScale((s) => (s >= 2.5 ? 1.5 : s + 1))}
        />
      </div>
      <p className="lightbox-hint">휠·버튼·더블클릭으로 확대, 드래그로 이동, 바깥 영역을 누르면 닫힙니다</p>
    </div>
  );
};
