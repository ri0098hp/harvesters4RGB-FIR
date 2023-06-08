import os
from itertools import count
from typing import Tuple, cast

import cv2
import numpy as np
import ultralytics

from harvesters.core import Harvester

# User Parameters
RGB_shape: tuple = (2048, 1536)  # (w,h)
FIR_shape: tuple = (640, 512)  # (w,h)
ptRGB = np.array([[335, 408], [317, 1078], [1664, 444], [1671, 1103]], dtype=np.float32)
ptFIR = np.array([[37, 87], [23, 390], [606, 98], [614, 395]], dtype=np.float32)
persMatrix = cv2.getPerspectiveTransform(ptRGB, ptFIR)
k = np.load("data/homo_v1.npz")
homoMatrix = k["arr_0"]
H = homoMatrix @ persMatrix
FPS: float = 29.970
cti: str = "mvGenTLProducer.cti"  # GenTL config file name


def main() -> None:
    # Select a mode
    opt = get_config()
    ch, debug, det, calib, sep_mode, save_folder = (
        opt["ch"],
        opt["debug"],
        opt["det"],
        opt["calib"],
        opt["sep_mode"],
        opt["save_folder"],
    )

    # Connect to Cameraq
    h = Harvester()
    h.add_file(os.path.join(cast(str, os.getenv("GENICAM_GENTL64_PATH")), cti))
    h.update()
    models = [d.property_dict.get("model") for d in h.device_info_list]
    print(f"認識したデバイス: {models}")

    # Setup folders and files
    folder = os.path.join(save_folder, get_datetime())
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # MJPG < mp4v, MP4V < H264
    RGB_fp = os.path.join(folder, "RGB_raw.mp4")
    FIR_fp = os.path.join(folder, "FIR.mp4")

    # RGB-FIR mode
    if "STC_SCS312POE" in models and "FLIR AX5" in models and ch == 4:
        FIR_cam = h.create({"model": "FLIR AX5"})
        setup_FIRcam(FIR_cam.remote_device.node_map, sep_mode)
        FIR_cam.start()
        RGB_cam = h.create({"model": "STC_SCS312POE"})
        setup_RGBcam(RGB_cam.remote_device.node_map, sep_mode)
        RGB_cam.start()
        if debug == 0:
            os.makedirs(folder, exist_ok=True)
            RGB_video = cv2.VideoWriter(RGB_fp, fourcc, FPS, RGB_shape)
            FIR_video = cv2.VideoWriter(FIR_fp, fourcc, FPS, FIR_shape)
    # RGB only
    elif "STC_SCS312POE" in models and ch == 3:
        RGB_cam = h.create({"model": "STC_SCS312POE"})
        setup_RGBcam(RGB_cam.remote_device.node_map, sep_mode)
        RGB_cam.start()
        if debug == 0:
            os.makedirs(folder, exist_ok=True)
            RGB_video = cv2.VideoWriter(RGB_fp, fourcc, FPS, RGB_shape)
    # FIR only
    elif "FLIR AX5" in models and ch == 1:
        FIR_cam = h.create({"model": "FLIR AX5"})
        setup_FIRcam(FIR_cam.remote_device.node_map, sep_mode)
        FIR_cam.start()
        if debug == 0:
            os.makedirs(folder, exist_ok=True)
            FIR_video = cv2.VideoWriter(FIR_fp, fourcc, FPS, FIR_shape)
    # exception handling
    else:
        print("E: Cannot find any devices. Please check your connection and restart.")
        h.reset()
        return
    # initialize RGB, FIR val
    RGB = np.zeros((RGB_shape[1], RGB_shape[0], 3))
    FIR = np.zeros((FIR_shape[1], FIR_shape[0], 3))

    # setup model
    if det:
        print("setup YOLOv8...")
        detecter = ultralytics.YOLO(f"weights/{det}")

    # capture start
    print("start")
    try:
        print()
        # RGB-FIR mode
        if "STC_SCS312POE" in models and "FLIR AX5" in models:
            for frame in count():
                FIR, FIR_fps = get_camdata(FIR_cam, "FIR")
                RGB, RGB_fps = get_camdata(RGB_cam, "RGB")
                if frame % 5 == 0:
                    print("\033[1A", end="")
                    print(f"processing... at {frame} frame / {RGB_fps:.3f} x {FIR_fps:.3f} FPS")
                if debug == 0:
                    RGB_video.write(RGB)
                    FIR_video.write(FIR)
                RGB = cv2.warpPerspective(RGB, H, (640, 512))
                if calib:
                    RGB = detect_circle(RGB, False)
                    FIR = detect_circle(FIR, True)
                if det:
                    RGB, FIR = detect(detecter, cv2.merge((RGB, FIR[:, :, 0])))
                concat = np.concatenate((RGB, FIR), axis=1)
                cv2.namedWindow("RGB-FIR")
                cv2.imshow("RGB-FIR", concat)
                if cv2.waitKey(10) == ord("q"):
                    break
        # RGB only
        elif "STC_SCS312POE" in models:
            for frame in count():
                RGB, RGB_fps = get_camdata(RGB_cam, "RGB")
                if frame % 5 == 0:
                    print("\033[1A", end="")
                    print(f"processing... at {frame} frame / {RGB_fps:.3f} FPS")
                if debug == 0:
                    RGB_video.write(RGB)
                RGB = cv2.warpPerspective(RGB, H, (640, 512))
                if calib:
                    RGB = detect_circle(RGB, False)
                if det:
                    RGB = detect(detecter, RGB)
                cv2.namedWindow("RGB")
                cv2.imshow("RGB", RGB)
                if cv2.waitKey(10) == ord("q"):
                    break
        # FIR only
        elif "FLIR AX5" in models:
            for frame in count():
                FIR, FIR_fps = get_camdata(FIR_cam, "FIR")
                if frame % 5 == 0:
                    print("\033[1A", end="")
                    print(f"processing... at {frame} frame / {FIR_fps:.3f} FPS")
                if debug == 0:
                    FIR_video.write(FIR)
                if calib:
                    FIR = detect_circle(FIR, True)
                if det:
                    FIR = detect(detecter, FIR)
                cv2.namedWindow("FIR")
                cv2.imshow("FIR", FIR)
                if cv2.waitKey(10) == ord("q"):
                    break
    # exception handling
    except Exception as e:
        print(f"Error: {e}")
    # release all handlers
    finally:
        if "STC_SCS312POE" in models and "FLIR AX5" in models:
            RGB_cam.stop()
            RGB_cam.destroy()
            FIR_cam.stop()
            FIR_cam.destroy()
            if debug == 0:
                RGB_video.release()
                FIR_video.release()
        elif "STC_SCS312POE" in models:
            RGB_cam.stop()
            RGB_cam.destroy()
            if debug == 0:
                RGB_video.release()
        elif "FLIR AX5" in models:
            FIR_cam.stop()
            FIR_cam.destroy()
            if debug == 0:
                FIR_video.release()
        cv2.destroyAllWindows()
        print("fin")
        h.reset()


# --------------------------------------------------
# get date and time now
# --------------------------------------------------
def get_datetime() -> str:
    import datetime

    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, "JST")
    now = datetime.datetime.now(JST)
    return now.strftime("%Y%m%d_%H%M")


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
        raise BaseException(print(f"E: 相対パスの引数ミス [{attr}]"))
    return os.path.join(datadir, filename)


# --------------------------------------------------
# reading parameters from setting.yaml
# --------------------------------------------------
def get_config() -> dict:
    import pprint

    import yaml

    config_ini_path = rel2abs_path("setting.yaml", "exe")
    # yamlファイルが存在するかチェック
    if os.path.exists(config_ini_path):
        # yamlファイルが存在する場合、ファイルを読み込む
        with open(config_ini_path, encoding="utf-8", errors="ignore") as f:
            opt = yaml.safe_load(f)
            pprint.pprint(opt)
        assert len(opt.keys()) == 12, print("setting.yamlのkey数が間違っています")
        return opt
    else:
        raise Exception(print("E: setting.iniが見つかりません\n"))


# --------------------------------------------------
# setup RGBcam by GenICam parameters
# --------------------------------------------------
def setup_RGBcam(RGB_config, sep_mode: bool) -> None:
    if sep_mode == 1:
        RGB_config.TriggerMode.value = "Off"
        RGB_config.AcquisitionFrameRate.value = FPS  # - 0.00375
    else:
        RGB_config.TriggerMode.value = "On"
        RGB_config.TriggerSource.value = "Line0"
        RGB_config.TriggerActivation.value = "LevelHigh"
        RGB_config.LineDebounceTime.value = 0
    RGB_config.ExposureAuto.value = "Continuous"
    RGB_config.GainAuto.value = "Continuous"
    RGB_config.TargetBrightness.value = 128
    RGB_config.AGCRange.value = 208


# --------------------------------------------------
# setup FIRcam by GenICam parameters
# --------------------------------------------------
def setup_FIRcam(FIR_config, sep_mode: bool) -> None:
    if sep_mode == 1:
        FIR_config.SyncMode.value = "Disabled"
    else:
        FIR_config.SyncMode.value = "SelfSyncMaster"
    FIR_config.AcquisitionMode.value = "Continuous"


# --------------------------------------------------
# obtain and covert GigE binary to cv2 image array
# --------------------------------------------------
def get_camdata(cam, flag: str) -> Tuple[np.ndarray, int]:
    # set timeout for the shutter of FIR cam
    with cam.fetch(timeout=3) as buffer:
        framerate = cam.statistics.fps
        component = buffer.payload.components[0]
        width = component.width
        height = component.height
        data = component.data.reshape(height, width)
        if flag == "RGB":
            img = cv2.cvtColor(data, cv2.COLOR_BayerBG2RGB)
        elif flag == "FIR":
            img = cv2.cvtColor(data, cv2.COLOR_GRAY2RGB)
        return img, framerate


# --------------------------------------------------
# detect circle grids and display markers
# --------------------------------------------------
def detect_circle(img: np.ndarray, bitwise: bool) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if bitwise:
        gray = cv2.bitwise_not(gray)
    ret, corners = cv2.findCirclesGrid(gray, (6, 4), None, flags=1)
    if ret:
        return cv2.drawChessboardCorners(img, (6, 4), corners, ret)
    else:
        return img


# --------------------------------------------------
# detect circle grids and display markers
# --------------------------------------------------
def detect(detecter: ultralytics.YOLO, img: np.ndarray):
    res = detecter(img, verbose=False)
    res_plotted = res[0].plot()
    return res_plotted[:, :, 0:3], np.stack((res_plotted[:, :, 3],) * 3, -1)


if __name__ == "__main__":
    # 文字コード化けを起こすのを回避
    if os.name == "nt":
        os.system("chcp 65001")
        os.system("cls")
    try:
        print("############################")
        print("\tRGB-FIRCamera")
        print("\tvYYYY.MM.DD")
        print("############################\n")
        main()
    except Exception as e:
        print(f"E: {e}")
    if os.name == "nt":
        os.system("PAUSE")
