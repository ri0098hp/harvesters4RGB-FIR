import glob
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import cv2
import numpy as np
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map

RGB_shape: Tuple = (1536, 2048)  # RGB解像度
FIR_shape: Tuple = (512, 640)  # FIR解像度
child_dirs: List[str] = ["RGB_raw", "RGB_crop", "RGB", "FIR", "concat", "RGB_homo"]
ratio: float = 0.45  # 縮小比
dy: int = 0  # -10? クロップのyシフト


# --------------------------------------------------
# main
# --------------------------------------------------
def main() -> None:
    root_folder, mp4tojpg, crop, calibrate, homo, merge = get_config()
    save_folder = ChooseFolder(root_folder)
    if mp4tojpg:
        mp4tojpg_converter(save_folder)
    if crop:
        save_folders = [os.path.join(save_folder, name) for name in child_dirs]
        os.makedirs(os.path.join(save_folder, child_dirs[1]), exist_ok=True)
        RGBraw_fps = glob.glob(os.path.join(save_folders[0], "*.jpg"))
        print("M: start cropping...")
        print(f"M: 読み込んだ画像数: {len(RGBraw_fps)}")
        thread_map(cropper, RGBraw_fps)
        print("M: fin\n")
    if calibrate:
        # setup perspective transsform kernel
        ptRGB = np.array([[335, 408], [317, 1078], [1664, 444], [1671, 1103]], dtype=np.float32)
        ptFIR = np.array([[37, 87], [23, 390], [606, 98], [614, 395]], dtype=np.float32)
        persMatrix = cv2.getPerspectiveTransform(ptRGB, ptFIR)

        os.makedirs(os.path.join(save_folder, child_dirs[2]), exist_ok=True)
        save_folders = [os.path.join(save_folder, name) for name in child_dirs]
        RGBraw_fps = glob.glob(os.path.join(save_folders[0], "*.jpg"))
        print("M: start calibrating...")
        with tqdm(total=len(RGBraw_fps), unit=" file") as pbar:
            tasks = []
            with ThreadPoolExecutor() as executor:
                for RGBraw_fp in RGBraw_fps:
                    task = executor.submit(calibrater, RGBraw_fp, child_dirs[2], persMatrix)
                    tasks += [task]
                for f in as_completed(tasks):
                    pbar.update(1)
        print("M: fin\n")
    if homo:
        save_folders = [os.path.join(save_folder, name) for name in child_dirs]
        os.makedirs(os.path.join(save_folder, child_dirs[5]), exist_ok=True)
        RGBraw_fps = glob.glob(os.path.join(save_folders[0], "*.jpg"))
        FIR_fps = glob.glob(os.path.join(save_folders[3], "*.jpg"))

        # setup perspective transsform kernel
        ptRGB = np.array([[335, 408], [317, 1078], [1664, 444], [1671, 1103]], dtype=np.float32)
        ptFIR = np.array([[37, 87], [23, 390], [606, 98], [614, 395]], dtype=np.float32)
        persMatrix = cv2.getPerspectiveTransform(ptRGB, ptFIR)
        # load homographic kernel
        k = np.load(rel2abs_path("data/homo_20221123.npz", "exe"))
        homoMatrix = k["arr_0"]
        # 合成
        H = homoMatrix @ persMatrix

        print("star perspective and homographic coverting on RGB imges...")
        with tqdm(total=len(RGBraw_fps), unit=" file") as pbar:
            tasks = []
            with ThreadPoolExecutor() as executor:
                for RGBraw_fp in RGBraw_fps:
                    task = executor.submit(calibrater, RGBraw_fp, child_dirs[5], H)
                    tasks += [task]
                for f in as_completed(tasks):
                    pbar.update(1)
        print("fin\n")
    if merge:
        os.makedirs(os.path.join(save_folder, child_dirs[4]), exist_ok=True)
        save_folders = [os.path.join(save_folder, name) for name in child_dirs]
        RGB_fps = glob.glob(os.path.join(save_folders[2], "*.jpg"))
        FIR_fps = glob.glob(os.path.join(save_folders[3], "*.jpg"))
        print("M: start merging RGB-FIR imgs...")
        thread_map(merger, RGB_fps, FIR_fps)
        print("fin\n")


# --------------------------------------------------
# rel to abs path (exe folder or extracted temp folder)
# --------------------------------------------------
def rel2abs_path(filename: str, attr: str) -> str:
    import sys

    if attr == "temp":  # 展開先フォルダと同階層
        datadir = os.path.dirname(__file__)
    elif attr == "exe":  # exeファイルと同階層の絶対パス
        datadir = os.path.dirname(sys.argv[0])
    else:
        raise Exception(print(f"E: 相対パスの引数ミス [{attr}]"))
    return os.path.join(datadir, filename)


# --------------------------------------------------
# choose saved folder of images named by date
# --------------------------------------------------
def ChooseFolder(root_folder: str) -> str:
    folders: List[str] = [fp for fp in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, fp))]
    msg: str = f"M: 日時フォルダ名を入力: {sorted(folders)}\n>> "
    save_folder: str = os.path.join(root_folder, input(msg))
    while not os.path.exists(save_folder):
        print("E: 存在しないフォルダ名です")
        save_folder = os.path.join(root_folder, input(msg))
    return save_folder


# --------------------------------------------------
# reading parameters from setting.ini
# --------------------------------------------------
def get_config() -> Tuple[str, bool, bool, bool, bool, bool]:
    import configparser

    config_ini = configparser.ConfigParser()
    config_ini_path = rel2abs_path("setting.ini", "exe")
    # iniファイルが存在するかチェック
    if os.path.exists(config_ini_path):
        # iniファイルが存在する場合、ファイルを読み込む
        with open(config_ini_path, encoding="utf-8") as fp:
            config_ini.read_file(fp)
            # iniの値取得
            read_default = config_ini["DEFAULT"]
            save_folder = rel2abs_path(read_default.get("save_folder"), "exe")
            mp4tojpg = bool(int(read_default.get("mp4tojpg")))
            crop = bool(int(read_default.get("crop")))
            calibrate = bool(int(read_default.get("calibrate")))
            homo = bool(int(read_default.get("homo")))
            merge = bool(int(read_default.get("merge")))
            print("###----------------------------------------###")
            print(f"保存先: {save_folder}")
            print(f"動画像変換: {mp4tojpg}")
            print(f"クロップ: {crop}")
            print(f"キャリブレーション: {calibrate}")
            print(f"カメラ行列によるキャリブレーション: {homo}")
            print(f"RGB-FIR結合: {merge}")
            print("###----------------------------------------###")
            return save_folder, mp4tojpg, crop, calibrate, homo, merge
    else:
        print("E: setting.iniが見つかりません\n")
        return rel2abs_path("out", "exe"), True, False, True, False, False


# --------------------------------------------------
# convert mp4 to jpeg files by ffmpeg
# --------------------------------------------------
def mp4tojpg_converter(save_folder) -> None:
    save_folders = [os.path.join(save_folder, name) for name in child_dirs]
    os.makedirs(os.path.join(save_folder, child_dirs[0]), exist_ok=True)
    os.makedirs(os.path.join(save_folder, child_dirs[3]), exist_ok=True)

    RGBraw = cv2.VideoCapture(os.path.join(save_folder, "RGB_raw.mp4"))
    FIR = cv2.VideoCapture(os.path.join(save_folder, "FIR.mp4"))
    flag: str = "RGBFIR"
    if not RGBraw.isOpened():
        print("E: RGBraw.mp4 file is not existing")
        flag = flag.replace("RGB", "")
    if not FIR.isOpened():
        print("E: FIR.mp4 file is not existing")
        flag = flag.replace("FIR", "")
    if os.path.exists(os.path.join(save_folders[0], "1.jpg")):
        print(f"E: already img files in {child_dirs[0]} are existing")
        flag = flag.replace("RGB", "")
    if os.path.exists(os.path.join(save_folders[3], "1.jpg")):
        print(f"E: already img files in {child_dirs[3]} are existing")
        flag = flag.replace("FIR", "")

    try:
        if "RGB" in flag:
            print("M: start extracting 1 frame per sec from RGB_raw.mp4 ...")
            id: int = 0  # 書き出しフレーム番号
            num: int = 0  # 書き出すファイルの連番号
            th: int = RGBraw.get(cv2.CAP_PROP_FPS)  # 1FPSで書き出す
            frames: int = int(RGBraw.get(cv2.CAP_PROP_FRAME_COUNT))  # 動画の総フレーム数
            with tqdm(total=frames // th, unit=" frame") as pbar:
                tasks = []
                with ThreadPoolExecutor() as executor:
                    for _ in range(frames):
                        id += 1
                        if id >= th:
                            num += 1
                            id = 0
                            task = executor.submit(
                                cv2.imwrite,
                                os.path.join(save_folders[0], f"{num}.jpg"),
                                RGBraw.read()[1],
                                [cv2.IMWRITE_JPEG_QUALITY, 100],
                            )
                            tasks += [task]
                    for f in as_completed(tasks):
                        pbar.update(1)

        if "FIR" in flag:
            print("M: start extracting 1 frame per sec from FIR.mp4 ...")
            id = 0
            num = 0
            th = FIR.get(cv2.CAP_PROP_FPS)
            frames = int(FIR.get(cv2.CAP_PROP_FRAME_COUNT))  # 動画の総フレーム数
            with tqdm(total=frames // th, unit=" frame") as pbar:
                tasks = []
                with ThreadPoolExecutor() as executor:
                    for _ in range(frames):
                        id += 1
                        if id >= th:
                            num += 1
                            id = 0
                            task = executor.submit(
                                cv2.imwrite,
                                os.path.join(save_folders[3], f"{num}.jpg"),
                                FIR.read()[1],
                                [cv2.IMWRITE_JPEG_QUALITY, 100],
                            )
                            tasks += [task]
                    for f in as_completed(tasks):
                        pbar.update(1)

    except FileNotFoundError:
        print("E: ffmpegがインストールされていないか、PATHが通っていません")
    except Exception as e:
        print(f"E: {e}")
    print("M: fin\n")


# --------------------------------------------------
# cropping on FIR image size
# --------------------------------------------------
def cropper(RGBraw_fp) -> None:
    RGBcrop_fp = RGBraw_fp.replace(child_dirs[0], child_dirs[1])
    if os.path.exists(RGBcrop_fp):
        # print(f'\nE: file is existing at "{RGBcrop_fp}"')
        return
    y: int = int((RGB_shape[0] * ratio - FIR_shape[0]) / 2)
    x: int = int((RGB_shape[1] * ratio - FIR_shape[1]) / 2)
    RGB = cv2.resize(cv2.imread(RGBraw_fp), dsize=None, fx=ratio, fy=ratio)
    RGBcrop = RGB[y + dy : y + dy + FIR_shape[0], x : x + FIR_shape[1]]
    cv2.imwrite(RGBcrop_fp, RGBcrop)


# --------------------------------------------------
# calibrating by PerspectiveTransform
# --------------------------------------------------
def calibrater(RGBraw_fp, dst_dir, persMatrix) -> None:
    RGB_fp = RGBraw_fp.replace(child_dirs[0], dst_dir)
    if os.path.exists(RGB_fp):
        # print(f'\nE: file is existing at "{RGB_fp}"')
        return
    RGBraw = cv2.imread(RGBraw_fp)
    RGB = cv2.warpPerspective(RGBraw, persMatrix, FIR_shape[::-1])
    cv2.imwrite(RGB_fp, RGB)


# --------------------------------------------------
# merging RGB and FIR images
# --------------------------------------------------
def merger(RGB_fp, FIR_fp) -> None:
    concat_fp = RGB_fp.replace(os.sep + child_dirs[2] + os.sep, os.sep + child_dirs[4] + os.sep)
    if os.path.exists(concat_fp):
        # print(f'\nE: file is existing at "{concat_fp}"')
        return
    RGB = cv2.imread(RGB_fp)
    FIR = cv2.imread(FIR_fp)
    concat = np.concatenate((RGB, FIR), axis=1)
    cv2.imwrite(concat_fp, concat)


if __name__ == "__main__":
    os.system("chcp 65001")
    os.system("cls")
    try:
        main()
    except Exception as e:
        print(f"E: {e}")
    os.system("PAUSE")
