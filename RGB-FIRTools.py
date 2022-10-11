import glob
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import cv2
import numpy as np
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map

RGB_shape: Tuple = (1536, 2048)  # RGB解像度
FIR_shape: Tuple = (512, 640)  # FIR解像度
child_dirs: List[str] = ["RGB_raw", "RGB_crop", "RGB", "FIR", "concat", "RGB_mtx", "FIR_mtx"]
ratio: float = 0.45  # 縮小比
dy: int = -10  # クロップのyシフト


# --------------------------------------------------
# main
# --------------------------------------------------
def main() -> None:
    root_folder, mp4tojpg, crop, calibrate, cammtx, merge = get_config()
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
                    task = executor.submit(calibrater, RGBraw_fp, persMatrix)
                    tasks += [task]
                for f in as_completed(tasks):
                    pbar.update(1)
        print("M: fin\n")
    if cammtx:
        save_folders = [os.path.join(save_folder, name) for name in child_dirs]
        os.makedirs(os.path.join(save_folder, child_dirs[5]), exist_ok=True)
        os.makedirs(os.path.join(save_folder, child_dirs[6]), exist_ok=True)
        RGBraw_fps = glob.glob(os.path.join(save_folders[0], "*.jpg"))
        FIR_fps = glob.glob(os.path.join(save_folders[3], "*.jpg"))

        # RGB
        k = np.load(rel2abs_path("data/RGB_cammtx.npz", "exe"))
        folders = [os.sep + d + os.sep for d in [child_dirs[0], child_dirs[5]]]
        print("start camera calibrating RGB imges...")
        with tqdm(total=len(RGBraw_fps), unit=" file") as pbar:
            tasks = []
            with ThreadPoolExecutor() as executor:
                for fp in RGBraw_fps:
                    task = executor.submit(camera_mtx, fp, k, folders)
                    tasks += [task]
                for f in as_completed(tasks):
                    pbar.update(1)
        print("fin")

        # FIR
        k = np.load(rel2abs_path("data/FIR_cammtx.npz", "exe"))
        folders = [os.sep + d + os.sep for d in [child_dirs[3], child_dirs[6]]]
        print("start camera calibrating FIR imges...")
        with tqdm(total=len(FIR_fps), unit=" file") as pbar:
            tasks = []
            with ThreadPoolExecutor() as executor:
                for fp in FIR_fps:
                    task = executor.submit(camera_mtx, fp, k, folders)
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


# --------------------------------------------------S
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
            cammtx = bool(int(read_default.get("cammtx")))
            merge = bool(int(read_default.get("merge")))
            print("###----------------------------------------###")
            print(f"保存先: {save_folder}")
            print(f"動画像変換: {mp4tojpg}")
            print(f"クロップ: {crop}")
            print(f"キャリブレーション: {calibrate}")
            print(f"カメラ行列によるキャリブレーション: {cammtx}")
            print(f"RGB-FIR結合: {merge}")
            print("###----------------------------------------###")
            return save_folder, mp4tojpg, crop, calibrate, cammtx, merge
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

    RGBraw_fp = os.path.join(save_folder, "RGB_raw.mp4")
    FIR_fp = os.path.join(save_folder, "FIR.mp4")
    RGBimg_fps = os.path.join(save_folders[0], "%d.jpg")
    FIRimg_fps = os.path.join(save_folders[3], "%d.jpg")
    flag: str = "RGBFIR"
    if not os.path.exists(RGBraw_fp):
        print(f"E: file is not existing at {RGBraw_fp}")
        flag = flag.replace("RGB", "")
    if not os.path.exists(FIR_fp):
        print(f"E: file is not existing at {FIR_fp}")
        flag = flag.replace("FIR", "")
    if os.path.exists(RGBimg_fps.replace("%d", "1")):
        print(f"E: already files in {child_dirs[0]} are existing")
        flag = flag.replace("RGB", "")
    if os.path.exists(FIRimg_fps.replace("%d", "1")):
        print(f"E: already files in {child_dirs[3]} are existing")
        flag = flag.replace("FIR", "")

    try:
        if "RGB" in flag:
            print("M: start extracting 1 frame per sec from RGB_raw.mp4 ...")
            cmd = [
                "ffmpeg",
                "-loglevel",
                "error",
                "-i",
                RGBraw_fp,
                "-qscale",
                "0",
                "-start_number",
                "1",
                "-r",
                "1",
                RGBimg_fps,
            ]
            subprocess.run(cmd)
        if "FIR" in flag:
            print("M: start extracting 1 frame per sec from FIR.mp4 ...")
            cmd = [
                "ffmpeg",
                "-loglevel",
                "error",
                "-i",
                FIR_fp,
                "-qscale",
                "0",
                "-start_number",
                "1",
                "-r",
                "1",
                FIRimg_fps,
            ]
            subprocess.run(cmd)
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
def calibrater(RGBraw_fp, persMatrix) -> None:
    RGB_fp = RGBraw_fp.replace(child_dirs[0], child_dirs[2])
    if os.path.exists(RGB_fp):
        # print(f'\nE: file is existing at "{RGB_fp}"')
        return
    RGBraw = cv2.imread(RGBraw_fp)
    RGB = cv2.warpPerspective(RGBraw, persMatrix, FIR_shape[::-1])
    cv2.imwrite(RGB_fp, RGB)


# --------------------------------------------------
# calibrating by using camera mtrix
# --------------------------------------------------
def camera_mtx(fp, k, folders) -> None:
    mtx = k["arr_0"]
    dist = k["arr_1"]
    newcameramtx = k["arr_2"]
    save_fp = fp.replace(folders[0], folders[1])
    if os.path.exists(save_fp):
        # print("already calibrated file is existing")
        return
    img = cv2.imread(fp)
    cv2.imwrite(save_fp, cv2.undistort(img, mtx, dist, None, newcameramtx))


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
