import cv2
from flask import Flask, Response
import atexit
import time

app = Flask(__name__)

# GStreamer 파이프라인 (640x480, 안정성 향상 옵션 포함)
gst_str_hw_accelerated = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! "
    "nvvidconv ! "
    "video/x-raw, width=640, height=480, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "appsink drop=1 max-buffers=1 sync=false"
)

# 전역 VideoCapture 객체
cap = cv2.VideoCapture(gst_str_hw_accelerated, cv2.CAP_GSTREAMER)

# 종료 시 자원 해제
@atexit.register
def cleanup():
    if cap.isOpened():
        cap.release()
        print("VideoCapture 자원 해제됨.")

def restart_capture():
    """VideoCapture 재시작"""
    global cap
    cap.release()
    time.sleep(1)
    cap = cv2.VideoCapture(gst_str_hw_accelerated, cv2.CAP_GSTREAMER)
    print("VideoCapture 재시작됨")

def gen_frames():
    """MJPEG 프레임 생성기"""
    global cap
    retry_count = 0
    while True:
        success, frame = cap.read()
        if not success or frame is None:
            retry_count += 1
            print(f"프레임 읽기 실패 ({retry_count})")

            if retry_count > 10:
                restart_capture()
                retry_count = 0
            time.sleep(0.1)
            continue

        retry_count = 0  # 성공 시 초기화

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            print("JPEG 인코딩 실패")
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return """
    <html>
      <head>
        <title>Jetson 실시간 카메라 스트리밍</title>
      </head>
      <body>
        <h1>640x480 실시간 스트리밍</h1>
        <img src="/video_feed" width="640" height="480">
      </body>
    </html>
    """

if __name__ == "__main__":
    if not cap.isOpened():
        print("GStreamer 파이프라인을 열 수 없습니다.")
        exit(1)
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

