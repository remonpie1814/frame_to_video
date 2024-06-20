import time
import subprocess
import threading
import cv2
import os
from collections import deque

class CamBuffer:
    def __init__(self, url, buffer_size, min_width=480, min_height=270):
        self.url = url
        self.frames = deque(maxlen=buffer_size)
        self.status = False
        self.isstop = False
        self.capture = cv2.VideoCapture(url)
        self.min_width = min_width
        self.min_height = min_height

    def start(self):
        self.isstop = False
        t1 = threading.Thread(target=self.queryframe, daemon=True)
        t1.start()

    def stop(self):
        self.isstop = True

    def reset(self):
        self.stop()
        self.capture.release()
        self.set_cam(self.url)
        self.start()

    def reset_buffer(self):
        self.frames.clear()

    def get_resolution(self):
        return [max(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)//2, self.min_width), max(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)//2, self.min_height)]
    
    def set_cam(self, url):
        self.capture = cv2.VideoCapture(url)
        self.reset_buffer()

    def queryframe(self):
        try:
            while (not self.isstop):
                self.status, tmp = self.capture.read()
                if not self.status:
                    raise Exception("cctv 영상을 가져올 수 없습니다.")
                tmp = cv2.resize(tmp, (max(tmp.shape[1]//2, self.min_width), max(tmp.shape[0]//2, self.min_height)))
                self.frames.append(tmp)                
        except Exception as e:
            print(e)
            print("reset...")
        finally:
            self.reset()

class FrameToVideo:
    def __init__(self, cam:CamBuffer, video_length, usegpu=True):
        """
            Parameters:
            - video_length: 비디오의 재생시간. 초 단위.
            - usegpu: gpu를 써서 ffmpeg를 가속할지 여부.
        """
        self.isstop = False
        self.cam = cam
        self.video_url = "./video/video.mp4"
        self.resolution = self.cam.get_resolution()
        if usegpu:
            self.command = ['ffmpeg',                      
                '-y',
                '-hwaccel', 'cuda',  # 하드웨어 가속 추가
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', "{}x{}".format(round(self.resolution[0]),round(self.resolution[1])),
                '-r', str(30),
                '-i', '-',
                '-t', f'{video_length}',
                '-c:v', 'h264_nvenc',  # NVENC를 사용하여 인코딩
                '-pix_fmt', 'yuv420p',
            self.video_url]
        else:
            self.command =  [
                'ffmpeg',
                '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', "{}x{}".format(round(self.resolution[0]), round(self.resolution[1])),
                '-r', str(30),
                '-i', '-',
                '-t', f'{video_length}',
                '-c:v', 'libx264', 
                '-pix_fmt', 'yuv420p',
                self.video_url
            ]

    def run_async(self):
        if not os.path.exists(os.path.dirname(self.video_url)):
            os.makedirs(os.path.dirname(self.video_url))
        self.isstop = False
        # ffmpeg 프로세스 시작
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE)
        # videocapture에서 프레임을 가져오는 스레드
        self.cam.start()
        time.sleep(0.5)
        t1 = threading.Thread(target=self.getframe, daemon=True)
        t1.start()
    
    def run(self):
        self.captures = deque(maxlen=self.cam.frames.maxlen)
        # ffmpeg 프로세스 시작
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE)
        # videocapture에서 프레임을 가져오는 스레드
        self.cam.start()
        while True:
            not_frame_count = 0
            if len(self.cam.frames)<1:
                not_frame_count += 1
                print("not frame!")
                time.sleep(0.1)
                if not_frame_count >= 30 * 60 * 3:
                    print(f"not frame for 3 minutes... reset camera...")
                    self.cam.reset()
                continue
            self.captures.append(self.cam.frames.popleft())
            if len(self.captures) >= self.captures.maxlen:
                break

        self.cam.stop()
        while self.captures:
            frame = self.captures.popleft()
            self.process.stdin.write(frame.tobytes())
        
        self.process.wait(timeout=10)
        self.process.kill()
        print("all process done.")

    def set_video_url(self, stream_url):
        print(stream_url)
        self.video_url = stream_url
        self.command[-1] = self.video_url

    def getframe(self):
        while (not self.isstop):
            not_frame_count = 0
            if len(self.cam.frames)<1:
                not_frame_count += 1
                print("not frame!")
                time.sleep(0.1)
                if not_frame_count >= 30 * 60 * 3:
                    print(f"not frame for 3 minutes... reset camera...")
                    self.cam.reset()
                continue
            frame = self.cam.frames.popleft()
            self.process.stdin.write(frame.tobytes())


def run(video_url:str, save_video_length:int, save_folder:str, save_video_name:str, usegpu=True, fps=30):
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    cam = CamBuffer(video_url, fps*save_video_length)
    process = FrameToVideo(cam, save_video_length, usegpu)
    process.set_video_url(os.path.join(save_folder, save_video_name))
    process.run()


if __name__ == "__main__":    
    run("http://112.166.0.196:7081/live/dlf&EH0174&/SELF/playlist.m3u8",10,"stream","video.mp4",True)