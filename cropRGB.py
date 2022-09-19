import cv2
import glob
import os
from tqdm import tqdm
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
    RGB_shape: List[int] = [1536, 2048]  # RGB解像度
    FIR_shape: List[int] = [640, 512]  # FIR解像度
    ratio: float = 0.45  # 縮小比

    save_folder = ChooseFolder()
    child_dirs: List[str] = ['RGB_raw', 'RGB_crop', 'RGB', 'FIR']
    os.makedirs(os.path.join(save_folder, child_dirs[1]), exist_ok=True)
    save_folders = [os.path.join(save_folder, name) for name in child_dirs]
    RGBraw_fps = glob.glob(os.path.join(save_folders[0], '*.jpg'))
    print(f'読み込んだ画像数: {len(RGBraw_fps)}')

    y: int = int((RGB_shape[0] * ratio - FIR_shape[0]) / 2)
    x: int = int((RGB_shape[1] * ratio - FIR_shape[1]) / 2)
    print('\nstart')
    for RGBraw_fp in tqdm(RGBraw_fps, unit=' file'):
        RGBcrop_fp = RGBraw_fp.replace(child_dirs[0], child_dirs[3])
        if os.path.exists(RGBcrop_fp):
            print(f'\nE: file is existing at "{RGBcrop_fp}"')
            break
        RGB = cv2.resize(cv2.imread(RGBraw_fp), dsize=None, fx=ratio, fy=ratio)
        RGBcrop = RGB[y:y+FIR_shape[0], x:x+FIR_shape[1]]
        cv2.imwrite(RGBcrop_fp, RGBcrop)
    print('fin')


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
