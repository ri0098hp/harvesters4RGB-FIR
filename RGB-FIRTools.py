import os
import cv2
import glob
import subprocess
import numpy as np
from tqdm import tqdm
from typing import List, Tuple


RGB_shape: Tuple = (1536, 2048)  # RGB解像度
FIR_shape: Tuple = (512, 640)  # FIR解像度
child_dirs: List[str] = ['RGB_raw', 'RGB_crop', 'RGB', 'FIR', 'concat']
ratio: float = 0.45  # 縮小比


# --------------------------------------------------
# rel to abs path (exe folder or extracted temp folder)
# --------------------------------------------------
def rel2abs_path(filename: str, attr: str) -> str:
    import sys
    if attr == 'temp':  # 展開先フォルダと同階層
        datadir = os.path.dirname(__file__)
    elif attr == 'exe':  # exeファイルと同階層の絶対パス
        datadir = os.path.dirname(sys.argv[0])
    else:
        raise BaseException(print(f'E: 相対パスの引数ミス [{attr}]'))
    return os.path.join(datadir, filename)


# --------------------------------------------------
# choose saved folder of images named by date
# --------------------------------------------------
def ChooseFolder() -> str:
    root_folder: str = rel2abs_path(r'out', 'exe')  # root folder for saving
    msg: str = 'M: 日時フォルダ名を入力 (例: 20180903_1113): '
    save_folder: str = os.path.join(root_folder, input(msg))
    while not os.path.exists(save_folder):
        print('E: 存在しないフォルダ名です')
        save_folder = os.path.join(root_folder, input(msg))
    return save_folder


# --------------------------------------------------
# convert mp4 to jpeg files by ffmpeg
# --------------------------------------------------
def mp4tojpg_converter(save_folder) -> None:
    save_folders = [os.path.join(save_folder, name) for name in child_dirs]
    os.makedirs(os.path.join(save_folder, child_dirs[0]), exist_ok=True)
    os.makedirs(os.path.join(save_folder, child_dirs[3]), exist_ok=True)

    RGBraw_fp = os.path.join(save_folder, 'RGB.mp4')
    FIR_fp = os.path.join(save_folder, 'FIR.mp4')
    RGBimg_fps = os.path.join(save_folders[0], '%04d.jpg')
    FIRimg_fps = os.path.join(save_folders[3], '%04d.jpg')
    if os.path.exists(RGBimg_fps.replace('%04d', '0001')):
        print(f'E: 既に{child_dirs[0]}フォルダにファイルが存在しています')
        return
    elif os.path.exists(FIRimg_fps.replace('%04d', '0001')):
        print(f'E: 既に{child_dirs[3]}フォルダにファイルが存在しています')
        return
    elif not os.path.exists(RGBraw_fp) and not os.path.exists(FIR_fp):
        print(f'\nE: file is not existing at "{RGBraw_fp}" or "{FIR_fp}"')
        return

    try:
        print('M: start RGB.mp4 converting...')
        cmd = ['ffmpeg',
               '-loglevel', 'error',
               '-i', RGBraw_fp,
               '-q:v', '1',
               '-r', '29.97',
               RGBimg_fps]
        subprocess.run(args=cmd, stdout=subprocess.DEVNULL)
        print('M: start FIR.mp4 converting...')
        cmd = ['ffmpeg',
               '-loglevel', 'error',
               '-i', FIR_fp,
               '-q:v', '1',
               '-r', '29.97',
               FIRimg_fps]
        subprocess.run(cmd, stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        print('E: ffmpegがインストールされていないか、PATHが通っていません')
    except Exception as e:
        print(f'E: {e}')
    print('M: fin\n')


# --------------------------------------------------
# cropping on FIR image size
# --------------------------------------------------
def cropper(save_folder) -> None:
    save_folders = [os.path.join(save_folder, name) for name in child_dirs]
    os.makedirs(os.path.join(save_folder, child_dirs[1]), exist_ok=True)
    RGBraw_fps = glob.glob(os.path.join(save_folders[0], '*.jpg'))

    y: int = int((RGB_shape[0] * ratio - FIR_shape[0]) / 2)
    x: int = int((RGB_shape[1] * ratio - FIR_shape[1]) / 2)
    print('M: start cropping...')
    print(f'M: 読み込んだ画像数: {len(RGBraw_fps)}')
    for RGBraw_fp in tqdm(RGBraw_fps, unit=' file'):
        RGBcrop_fp = RGBraw_fp.replace(child_dirs[0], child_dirs[1])
        if os.path.exists(RGBcrop_fp):
            print(f'\nE: file is existing at "{RGBcrop_fp}"')
            break
        RGB = cv2.resize(cv2.imread(RGBraw_fp), dsize=None, fx=ratio, fy=ratio)
        RGBcrop = RGB[y:y+FIR_shape[0], x:x+FIR_shape[1]]
        cv2.imwrite(RGBcrop_fp, RGBcrop)
    print('M: fin\n')


# --------------------------------------------------
# calibrating by PerspectiveTransform
# --------------------------------------------------
def calibrater(save_folder) -> None:
    # setup perspective transform kernel
    ptRGB = np.array([[335, 408],
                      [317, 1078],
                      [1664, 444],
                      [1671, 1103]],
                     dtype=np.float32)
    ptFIR = np.array([[37, 87],
                      [23, 390],
                      [606, 98],
                      [614, 395]],
                     dtype=np.float32)
    persMatrix = cv2.getPerspectiveTransform(ptRGB, ptFIR)

    os.makedirs(os.path.join(save_folder, child_dirs[2]), exist_ok=True)
    save_folders = [os.path.join(save_folder, name) for name in child_dirs]
    RGBraw_fps = glob.glob(os.path.join(save_folders[0], '*.jpg'))
    print('M: start calibrating...')
    for RGBraw_fp in tqdm(RGBraw_fps, unit=' file'):
        RGB_fp = RGBraw_fp.replace(child_dirs[0], child_dirs[2])
        if os.path.exists(RGB_fp):
            print(f'\nE: file is existing at "{RGB_fp}"')
            break
        RGBraw = cv2.imread(RGBraw_fp)
        RGB = cv2.warpPerspective(RGBraw, persMatrix, FIR_shape[::-1])
        cv2.imwrite(RGB_fp, RGB)
    print('M: fin\n')


# --------------------------------------------------
# merging RGB and FIR images
# --------------------------------------------------
def merger(save_folder) -> None:
    os.makedirs(os.path.join(save_folder, child_dirs[4]), exist_ok=True)
    save_folders = [os.path.join(save_folder, name) for name in child_dirs]
    RGB_fps = glob.glob(os.path.join(save_folders[2], '*.jpg'))
    FIR_fps = glob.glob(os.path.join(save_folders[3], '*.jpg'))
    print('M: start merging...')
    for RGB_fp, FIR_fp in tqdm(zip(RGB_fps, FIR_fps), unit=' file'):
        concat_fp = os.path.join(save_folders[4], os.path.basename(RGB_fp))
        if os.path.exists(concat_fp):
            print(f'\nE: file is existing at "{concat_fp}"')
            break
        RGB = cv2.imread(RGB_fp)
        FIR = cv2.imread(FIR_fp)
        concat = np.concatenate((RGB, FIR), axis=1)
        cv2.imwrite(concat_fp, concat)
    print('M: fin\n')


def main() -> None:
    parent_dir = ChooseFolder()
    mp4tojpg_converter(parent_dir)
    cropper(parent_dir)
    calibrater(parent_dir)
    merger(parent_dir)


if __name__ == "__main__":
    os.system('chcp 65001')
    os.system('cls')
    try:
        main()
    except Exception as e:
        print(f'E: {e}')
    os.system('PAUSE')
