import os
from PIL import Image, ImageOps

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "images", "exams")

def auto_crop_white_margins(image_path):
    """
    Pillow 라이브러리를 기동하여, 시험지 캡처 이미지 외곽의 넓은 흰색 여백을 자동으로 완벽하게 잘라냅니다.
    - 그레이스케일 변환 및 임계치 이진화 적용
    - getbbox()를 활용한 실체 픽셀 영역 바운딩 박스 검출
    - 사방 10px의 안정적인 시각적 패딩 부여 후 타이트하게 크롭하여 덮어쓰기
    """
    try:
        with Image.open(image_path) as img:
            # 1. 픽셀 경계 판정을 위해 그레이스케일 변환
            gray = img.convert('L')
            
            # 2. 아주 연한 회색/흰색 영역(240~255)을 완전히 검은색(0)으로, 글자/유물 영역을 흰색(255)으로 반전 이진화
            # getbbox()는 검은색(0) 배경 속에서 흰색(양수 픽셀)이 존재하는 영역의 경계를 검출합니다.
            thresholded = gray.point(lambda p: 255 if p < 242 else 0)
            
            bbox = thresholded.getbbox()
            if not bbox:
                print(f"[-] 유효 픽셀 검출 실패 (건너뜀): {os.path.basename(image_path)}")
                return
                
            # 3. 글자가 뚝 잘리지 않도록 15px의 안전한 여백 패딩 적용
            padding = 15
            left = max(0, bbox[0] - padding)
            upper = max(0, bbox[1] - padding)
            right = min(img.width, bbox[2] + padding)
            lower = min(img.height, bbox[3] + padding)
            
            # 4. 이미지 크롭 및 저장 (덮어쓰기)
            cropped_img = img.crop((left, upper, right, lower))
            
            # 기존 이미지 크기 대비 개선율 계산
            orig_size = img.size
            new_size = cropped_img.size
            
            cropped_img.save(image_path, "JPEG")
            print(f"[+] 크롭 완료: {image_path.replace(IMAGES_DIR, '')} (이전: {orig_size} -> 이후: {new_size})")
            
    except Exception as e:
        print(f"[!] 크롭 실패: {os.path.basename(image_path)} ({str(e)})")

def process_all_exams():
    print("[*] 1,100개 기출문제 이미지 흰 여백 자동 크롭 알고리즘 구동 시작...")
    if not os.path.exists(IMAGES_DIR):
        print(f"[!] 에러: 기출문제 폴더가 존재하지 않습니다: {IMAGES_DIR}")
        return

    processed_count = 0
    # exams 폴더 아래의 모든 회차별 디렉토리 순회
    for root, dirs, files in os.walk(IMAGES_DIR):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                full_path = os.path.join(root, file)
                auto_crop_white_margins(full_path)
                processed_count += 1

    print(f"[+] 총 {processed_count}개 기출 이미지의 무의미한 흰색 패딩 여백이 제거되어 글자가 확대 최적화되었습니다!")

if __name__ == "__main__":
    process_all_exams()
