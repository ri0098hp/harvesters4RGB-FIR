import os
import subprocess
from typing import List


# --------------------------------------------------
# choose saved folder of images named by date
# --------------------------------------------------
def ChooseFolder() -> str:
    root_folder: str = r'out'  # root folder for saving
    msg: str = 'M: 日時フォルダ名を入力 (例: 20180903_1113): '
    save_folder: str = os.path.join(root_folder, input(msg))
    while not os.path.exists(save_folder):
        print('E: 存在しないフォルダ名です')
        save_folder = os.path.join(root_folder, input(msg))
    return save_folder


def main() -> None:
    save_folder = ChooseFolder()
    child_dirs: List[str] = ['RGB_raw', 'RGB_crop', 'RGB', 'FIR']
    save_folders = [os.path.join(save_folder, name) for name in child_dirs]
    os.makedirs(os.path.join(save_folder, child_dirs[0]), exist_ok=True)
    os.makedirs(os.path.join(save_folder, child_dirs[3]), exist_ok=True)

    RGBraw_fp = os.path.join(save_folder, 'RGB.mp4')
    RGBimg_fps = os.path.join(save_folders[0], '%04d.jpg')
    FIR_fp = os.path.join(save_folder, 'FIR.mp4')
    FIRimg_fps = os.path.join(save_folders[3], '%04d.jpg')
    if os.path.exists(RGBimg_fps.replace('%04d', '0001')):
        print(f'既に{child_dirs[0]}フォルダにファイルが存在しています')
        return
    elif os.path.exists(FIRimg_fps.replace('%04d', '0001')):
        print(f'既に{child_dirs[3]}フォルダにファイルが存在しています')
        return

    try:
        print('start RGB converting')
        cmd = ['ffmpeg',
               '-loglevel', 'error',
               '-i', RGBraw_fp,
               '-q:v', '1',
               '-r', '29.97',
               RGBimg_fps]
        subprocess.run(args=cmd, stdout=subprocess.DEVNULL)
        print('start FIR converting')
        cmd = ['ffmpeg',
               '-loglevel', 'error',
               '-i', FIR_fp,
               '-q:v', '1',
               '-r', '29.97',
               FIRimg_fps]
        subprocess.run(cmd, stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        print('ffmpegがインストールされていないか、PATHが通っていません')
    except Exception as e:
        print(e)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
