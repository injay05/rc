import cv2, sys, time
import numpy as np
import math
import requests
import paho.mqtt.publish as publish

broker_ip = "172.20.10.5"
topic = "car/control"

def pub_msg(msg):
    print(f"[PUB] {msg}")  # 확인용 출력
    publish.single(topic, msg, hostname=broker_ip)

url = 'http://172.20.10.2:8080/video_feed'
stream = requests.get(url, stream=True)
if stream.status_code != 200:
    print("Failed to connect to", url)
    exit()

bytes_buffer = b''

def extract_roi(frame):
    # 기존 방식 유지 (필요 시 여기만 바꾸면 됨)
    h, w = frame.shape[:2]
    roi_y1 = h - 130
    roi_y2 = h
    roi_x1 = 235  # 직접 지정
    roi_x2 = roi_x1 + 170
    roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
    return roi, roi_x1, roi_y1, roi_x2, roi_y2

last_detected = None  # ✅ 직전 감지된 위치 저장

try:
    for chunk in stream.iter_content(chunk_size=1024):
        bytes_buffer += chunk
        a = bytes_buffer.find(b'\xff\xd8')
        b = bytes_buffer.find(b'\xff\xd9')

        if a != -1 and b != -1:
            jpg = bytes_buffer[a:b + 2]
            bytes_buffer = bytes_buffer[b + 2:]

            img_array = np.frombuffer(jpg, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            frame = cv2.resize(frame, (640, 480))

            roi, roi_x1, roi_y1, roi_x2, roi_y2 = extract_roi(frame)

            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            lower_black = np.array([0, 0, 0])
            upper_black = np.array([180, 255, 100])
            binary = cv2.inRange(hsv, lower_black, upper_black)
            kernel = np.ones((3, 3), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

            # ✅ 외곽선 시각화 포함 (원본 구조 유지)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 100:
                    x, y, w, h = cv2.boundingRect(cnt)
                    cx, cy = x + w // 2, y + h // 2
                    print(f"[OBJECT] Detected black object at ({cx}, {cy}) with size ({w}x{h})")
                    cnt_shifted = cnt + np.array([[roi_x1, roi_y1]])
                    cv2.drawContours(frame, [cnt_shifted], -1, (0, 255, 0), 2)

            # ✅ 박스 5개 수동 정의 (센터: 30픽셀, 좌우 25픽셀씩, 최끝단 20픽셀씩)
            boxes = {
                "left3":  (0,   20,  (128, 0 , 128)),
                "left2":  (20,  45,  (255, 0, 255)),
                "left1":  (45,  70,  (255, 0, 0)),
                "center": (70, 100, (0, 255, 0)),
                "right1": (100, 125, (0, 165, 255)),
                "right2": (125, 150, (0, 140, 255)),
                "right3": (150, 170, (0, 0, 255))
            }

            current_detected = None  # ✅ 현재 감지된 위치

            for position, (x_start, x_end, color) in boxes.items():
                box = binary[:, x_start:x_end]
                black_ratio = np.sum(box == 255) / box.size
                is_detected = black_ratio > 0.2

                if is_detected and current_detected is None:
                    current_detected = position  # 첫 번째로 검출된 영역만 채택

                # 박스 시각화
                abs_x1 = roi_x1 + x_start
                abs_x2 = roi_x1 + x_end
                cv2.rectangle(frame, (abs_x1, roi_y1), (abs_x2, roi_y2), color, 2)
                cv2.putText(frame, position.upper(), (abs_x1 + 5, roi_y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # ✅ 이전 상태와 다를 때만 퍼블리시
            if current_detected and current_detected != last_detected:
                last_detected = current_detected

                if current_detected == "center":
                    pub_msg("go")
                elif current_detected == "right1":
                    pub_msg("right1")
                elif current_detected == "right2":
                    pub_msg("right2")
                elif current_detected == "right3":
                    pub_msg("right3")
                elif current_detected == "left1":
                    pub_msg("left1")
                elif current_detected == "left2":
                    pub_msg("left2")
                elif current_detected == "left3":
                    pub_msg("left3")
            elif current_detected is None and last_detected is not None:
                last_detected = None
                pub_msg("back")

            cv2.imshow("Stream Line Detection", frame)

            if cv2.waitKey(5) & 0xFF == 27:
                break

except KeyboardInterrupt:
    print("\nStopped by user.")
finally:
    cv2.destroyAllWindows()
