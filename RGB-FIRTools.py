import glob
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
import cv2
import numpy as np
from itertools import repeat
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map

RGB_shape: Tuple = (1536, 2048)  # RGB解像度
FIR_shape: Tuple = (512, 640)  # FIR解像度

# setip kernels
# perspective transsform
ptRGB = np.array([[335, 408], [317, 1078], [1664, 444], [1671, 1103]], dtype=np.float32)
ptFIR = np.array([[37, 87], [23, 390], [606, 98], [614, 395]], dtype=np.float32)
persMatrix = cv2.getPerspectiveTransform(ptRGB, ptFIR)

# crop
ratio: float = 0.45  # 縮小比
dy: int = 0  # -10? クロップのyシフト


# --------------------------------------------------
# main
# --------------------------------------------------
def main() -> None:
    opt = get_config()
    save_folders = ChooseFolder(rel2abs_path(opt["save_folder"], "exe"))
    for save_folder in save_folders:
        print("\n#########################")
        print(f"M: process at {save_folder}")
        if opt["mp4tojpg"] != 0:
            mp4tojpg_converter(save_folder)
        if opt["crop"] != 0:
            os.makedirs(os.path.join(save_folder, "RGB_crop"), exist_ok=True)
            RGBraw_fps = glob.glob(os.path.join(save_folder, "RGB_raw", "*.jpg"))
            print("M: start cropping...")
            print(f"M: 読み込んだ画像数: {len(RGBraw_fps)}")
            thread_map(cropper, RGBraw_fps)
            print("M: fin")
        if opt["pers"] != 0:
            os.makedirs(os.path.join(save_folder, "RGB"), exist_ok=True)
            RGBraw_fps = glob.glob(os.path.join(save_folder, "RGB_raw", "*.jpg"))
            print("M: start calibrating...")
            with tqdm(total=len(RGBraw_fps), unit=" file") as pbar:
                tasks = []
                with ThreadPoolExecutor() as executor:
                    for RGBraw_fp in RGBraw_fps:
                        task = executor.submit(calibrater, RGBraw_fp, "RGB", persMatrix)
                        tasks += [task]
                    for f in as_completed(tasks):
                        pbar.update(1)
            print("M: fin")
        if opt["homo"] != 0:
            os.makedirs(os.path.join(save_folder, "RGB_homo"), exist_ok=True)
            RGBraw_fps = glob.glob(os.path.join(save_folder, "RGB_raw", "*.jpg"))
            FIR_fps = glob.glob(os.path.join(save_folder, "FIR", "*.jpg"))

            # load homographic kernel
            k = np.load(rel2abs_path(f'data/{opt["homo"]}', "exe"))
            homoMatrix = k["arr_0"]
            H = homoMatrix @ persMatrix

            print("start perspective and homographic coverting on RGB imges...")
            with tqdm(total=len(RGBraw_fps), unit=" file") as pbar:
                tasks = []
                with ThreadPoolExecutor() as executor:
                    for RGBraw_fp in RGBraw_fps:
                        task = executor.submit(calibrater, RGBraw_fp, "RGB_homo", H)
                        tasks += [task]
                    for f in as_completed(tasks):
                        pbar.update(1)
            print("M: fin")
        if opt["merge"] != 0:
            os.makedirs(os.path.join(save_folder, "concat"), exist_ok=True)
            RGB_fps = glob.glob(os.path.join(save_folder, opt["merge"], "*.jpg"))
            FIR_fps = glob.glob(os.path.join(save_folder, "FIR", "*.jpg"))
            print("M: start merging RGB-FIR imgs...")
            target_folders = repeat(opt["merge"], times=len(RGB_fps))
            thread_map(merger, target_folders, RGB_fps, FIR_fps)
            print("M: fin")
        if opt["fuse"] != 0:
            os.makedirs(os.path.join(save_folder, "fuse"), exist_ok=True)
            RGB_fps = glob.glob(os.path.join(save_folder, opt["fuse"], "*.jpg"))
            FIR_fps = glob.glob(os.path.join(save_folder, "FIR", "*.jpg"))
            print("M: start fusing RGB-FIR imgs...")
            target_folders = repeat(opt["fuse"], times=len(RGB_fps))
            thread_map(fuser, target_folders, RGB_fps, FIR_fps)
            print("M: fin")
        print("#########################")


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
def ChooseFolder(root_folder: str) -> List[str]:
    folders: List[str] = [fp for fp in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, fp))]
    save_folders: List[str] = [os.path.join(root_folder, target) for target in folders]
    msg: str = f'M: 日時フォルダ名を入力 ("all"で全て): {sorted(folders)}\n>> '
    target: str = input(msg)
    if target == "all":
        return save_folders
    save_folder = os.path.join(root_folder, target)
    while not os.path.exists(save_folder):
        print("E: 存在しないフォルダ名です")
        save_folder = os.path.join(root_folder, input(msg))
    return [save_folder]


# --------------------------------------------------
# reading parameters from setting.ini
# --------------------------------------------------
def get_config() -> dict:
    import yaml
    import pprint

    config_ini_path = rel2abs_path("setting.yaml", "exe")
    # iniファイルが存在するかチェック
    if os.path.exists(config_ini_path):
        # iniファイルが存在する場合、ファイルを読み込む
        with open(config_ini_path, errors="ignore") as f:
            opt = yaml.safe_load(f)
            pprint.pprint(opt)
        assert len(opt.keys()) == 10, print("setting.yamlのkeyが足りません")
        return opt
    else:
        raise Exception(print("E: setting.iniが見つかりません\n"))


# --------------------------------------------------
# convert mp4 to jpeg files by ffmpeg
# --------------------------------------------------
def mp4tojpg_converter(save_folder) -> None:
    import subprocess

    os.makedirs(os.path.join(save_folder, "RGB_raw"), exist_ok=True)
    os.makedirs(os.path.join(save_folder, "FIR"), exist_ok=True)

    RGBraw_fp: str = os.path.join(save_folder, "RGB_raw.mp4")
    FIR_fp: str = os.path.join(save_folder, "FIR.mp4")
    RGBimg_fps: str = os.path.join(save_folder, "RGB_raw", "%d.jpg")
    FIRimg_fps: str = os.path.join(save_folder, "FIR", "%d.jpg")
    flag: str = "RGBFIR"
    if not os.path.exists(RGBraw_fp):
        print(f"E: file is not existing at {RGBraw_fp}")
        flag = flag.replace("RGB", "")
    if not os.path.exists(FIR_fp):
        print(f"E: file is not existing at {FIR_fp}")
        flag = flag.replace("FIR", "")
    if os.path.exists(os.path.join(save_folder, "RGB_raw", "1.jpg")):
        print("E: already img files in RGB_raw are existing")
        flag = flag.replace("RGB", "")
    if os.path.exists(os.path.join(save_folder, "FIR", "1.jpg")):
        print("E: already img files in FIR are existing")
        flag = flag.replace("FIR", "")

    try:
        if "RGB" in flag:
            print("M: start extracting 1 frame per sec from RGB_raw.mp4 ...")
            cmd = [
                "ffmpeg",
                "-loglevel",
                "error",
                "-progress",
                "-",
                "-nostats",
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
                "-progress",
                "-",
                "-nostats",
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
    RGBcrop_fp = RGBraw_fp.replace("RGB_raw", "RGB_crop")
    if os.path.exists(RGBcrop_fp):
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
    RGB_fp = RGBraw_fp.replace("RGB_raw", dst_dir)
    if os.path.exists(RGB_fp):
        return
    RGBraw = cv2.imread(RGBraw_fp)
    RGB = cv2.warpPerspective(RGBraw, persMatrix, FIR_shape[::-1])
    cv2.imwrite(RGB_fp, RGB)


# --------------------------------------------------
# merging RGB and FIR images
# --------------------------------------------------
def merger(from_dir, RGB_fp, FIR_fp) -> None:
    concat_fp = RGB_fp.replace(os.sep + from_dir + os.sep, os.sep + "concat" + os.sep)
    if os.path.exists(concat_fp):
        return
    RGB = cv2.imread(RGB_fp)
    FIR = cv2.imread(FIR_fp)
    concat = np.concatenate((RGB, FIR), axis=1)
    cv2.imwrite(concat_fp, concat)


# --------------------------------------------------
# fuse RGB and FIR images
# --------------------------------------------------
def fuser(from_dir, RGB_fp, FIR_fp) -> None:
    fuse_fp = RGB_fp.replace(os.sep + from_dir + os.sep, os.sep + "fuse" + os.sep)
    if os.path.exists(fuse_fp):
        return
    RGB = cv2.imread(RGB_fp)
    FIR = cv2.imread(FIR_fp)
    fuse = cv2.addWeighted(src1=RGB, alpha=0.2, src2=FIR, beta=0.8, gamma=-20)
    cv2.imwrite(fuse_fp, fuse)


if __name__ == "__main__":
    os.system("chcp 65001")
    os.system("cls")
    try:
        main()
    except Exception as e:
        print(f"E: {e}")
    os.system("PAUSE")
