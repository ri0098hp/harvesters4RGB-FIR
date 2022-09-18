import cv2
import glob
import os
from tqdm import tqdm
from typing import List


def main():
    RGB_shape: List[int] = [1536, 2048]  # RGB解像度
    FIR_shape: List[int] = [640, 512]  # FIR解像度
    ratio: float = 0.45  # 縮小比

    root_folder: str = r'out'  # root folder for saving
    save_folder: str = os.path.join(root_folder, input('M: 再度日時フォルダ名を入力: '))
    while not os.path.exists(save_folder):
        print('E: 存在しないフォルダ名です')
        save_folder = os.path.join(root_folder, input('M: 再度日時フォルダ名を入力: '))
    child_dirs: List[str] = ['RGB_raw', 'RGB', 'FIR', 'RGB_crop']
    os.makedirs(os.path.join(save_folder, child_dirs[3]), exist_ok=True)
    save_folders = [os.path.join(save_folder, name) for name in child_dirs]
    RGBraw_fps: List[str] = glob.glob(os.path.join(save_folders[0], '*.jpg'))

    y: int = int((RGB_shape[0] * ratio - FIR_shape[0]) / 2)
    x: int = int((RGB_shape[1]*ratio - FIR_shape[1]) / 2)
    for RGBraw_fp in tqdm(RGBraw_fps, unit=' file'):
        RGBraw = cv2.imread(RGBraw_fp)
        RGB = cv2.resize(RGBraw, dsize=None, fx=ratio, fy=ratio)
        crop = RGB[y:y+FIR_shape[0], x:x+FIR_shape[1]]
        cv2.imwrite(RGBraw_fp.replace(child_dirs[0], child_dirs[3]), crop)
    print('fin')


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
