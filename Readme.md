### Frame To Video

ffmpeg를 사용해 영상의 주소를 받으면 정해진 시간만큼 녹화해서 mp4로 변환하는 프로그램

설치
pip install -r requirements.txt

ffmpeg 설치
https://ffmpeg.org/download.html

테스트 실행
python frame_to_video.py

모듈 사용방법
import run from frame_to_video

run(영상 주소, 녹화할 영상 길이, 녹화영상 저장폴더, 녹화영상 이름)
