import os
import cv2
import glob
import numpy as np
from tqdm import tqdm


def main() -> None:
    root_folder: str = r'out'  # root folder for saving
    save_folder = os.path.join(root_folder, input(
        'M: 日時フォルダ名を入力 (例: 20180903_1113): '))
    while not os.path.exists(save_folder):
        print('E: 存在しないフォルダ名です')
        save_folder = os.path.join(root_folder, input('M: 再度日時フォルダ名を入力: '))

    child_dirs = ['RGB_raw', 'RGB', 'FIR', 'concat']
    os.makedirs(os.path.join(child_dirs[2], 'RGB'), exist_ok=True)
    save_folders = [os.path.join(save_folder, name) for name in child_dirs]
    RGBraw_fps = glob.glob(os.path.join(save_folders[0], '*.jpg'))
    print('start converting')
    for RGBraw_fp in tqdm(RGBraw_fps, unit=' file'):
        RGB_fp = RGBraw_fp.replace('RGB_raw', 'RGB')
        if os.path.exists(RGB_fp):
            print('E: file is existing at {RGB_fp}')
            break
        cv2.imwrite(RGB_fp, calib(cv2.imread(RGBraw_fp)))
    print('fin')


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
# calbrating by PerspectiveTransform
# --------------------------------------------------
def calib(img) -> np.ndarray:
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
    # 射影変換
    persMatrix = cv2.getPerspectiveTransform(ptRGB, ptFIR)
    dst = cv2.warpPerspective(img, persMatrix, (640, 512))
    return dst


if __name__ == "__main__":
    main()
