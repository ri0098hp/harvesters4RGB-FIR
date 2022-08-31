from harvesters.core import Harvester
from itertools import count
from typing import cast
import numpy as np
import time
import cv2
import os


# User Parameters
RGB_shape: tuple = (2048, 1536)  # (w,h)
FIR_shape: tuple = (640, 512)  # (w,h)
FPS: float = 29.970
save_folder: str = r'./out'  # root folder for saving
cti: str = 'mvGenTLProducer.cti'  # GenTL config file name


# default: False, False, True
debug: bool = False  # disable making folder and files
calib: bool = False  # enable calibrate
sep_mode: bool = True  # set controling separate without sync


# --------------------------------------------------
# get date and time now
# --------------------------------------------------
def get_datetime() -> str:
    import datetime
    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, 'JST')
    now = datetime.datetime.now(JST)
    return now.strftime('%Y%m%d_%H%M')


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
# creating save-directory
# --------------------------------------------------
def make_dirs(folder: str) -> None:
    os.makedirs(os.path.join(folder, 'RGB_raw'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'RGB'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'FIR'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'concat'), exist_ok=True)


# --------------------------------------------------
# obtain and covert GigE binary to cv2 image array
# --------------------------------------------------
def get_camdata(cam, flag: str) -> np.ndarray:
    # set timeout for the shutter of FIR cam
    with cam.fetch(timeout=3) as buffer:
        component = buffer.payload.components[0]
        width = component.width
        height = component.height
        data = component.data.reshape(height, width)
        if flag == 'RGB':
            img = cv2.cvtColor(data, cv2.COLOR_BayerBG2RGB)
        elif flag == 'FIR':
            img = cv2.cvtColor(data, cv2.COLOR_GRAY2RGB)
        return img


# --------------------------------------------------
# detect circle grids and display markers
# --------------------------------------------------
def detect(img: np.ndarray, bitwise: bool) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if bitwise is True:
        gray = cv2.bitwise_not(gray)
    ret, corners = cv2.findCirclesGrid(gray, (6, 4), None, flags=1)
    if ret is True:
        return cv2.drawChessboardCorners(img, (6, 4), corners, ret)
    else:
        return img


# --------------------------------------------------
# detect circle grids and display markers
# --------------------------------------------------
def setup_RGBcam(RGB_config) -> None:
    if sep_mode is True:
        RGB_config.TriggerMode.value = 'Off'
        RGB_config.AcquisitionFrameRate.value = FPS
    else:
        RGB_config.TriggerMode.value = 'On'
        RGB_config.TriggerSource.value = 'Line0'
        RGB_config.TriggerActivation.value = 'LevelHigh'
        RGB_config.LineDebounceTime.value = 0
    RGB_config.ExposureAuto.value = 'Continuous'
    RGB_config.GainAuto.value = 'Continuous'
    RGB_config.TargetBrightness.value = 128
    RGB_config.AGCRange.value = 208


# --------------------------------------------------
# detect circle grids and display markers
# --------------------------------------------------
def setup_FIRcam(FIR_config) -> None:
    if sep_mode is True:
        FIR_config.SyncMode.value = 'Disabled'
    else:
        FIR_config.SyncMode.value = 'SelfSyncMaster'
    FIR_config.AcquisitionMode.value = 'Continuous'


def main():
    # Connect to Camera
    h = Harvester()
    h.add_file(os.path.join(cast(str, os.getenv('GENICAM_GENTL64_PATH')), cti))
    h.update()
    models = [d.property_dict.get('model') for d in h.device_info_list]
    print(f'Connected Devces: {models}')

    # Setup folders and files
    folder = os.path.join(save_folder, get_datetime())
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    RGB_fp = os.path.join(folder, 'RGB.mp4')
    FIR_fp = os.path.join(folder, 'FIR.mp4')

    # Select a mode
    # RGB-FIR mode
    if 'STC_SCS312POE' in models and 'FLIR AX5' in models:
        FIR_cam = h.create({'model': 'FLIR AX5'})
        setup_FIRcam(FIR_cam.remote_device.node_map)
        FIR_cam.start()
        RGB_cam = h.create({'model': 'STC_SCS312POE'})
        setup_RGBcam(RGB_cam.remote_device.node_map)
        RGB_cam.start()
        if debug is not True:
            make_dirs(folder)
            RGB_video = cv2.VideoWriter(RGB_fp, fourcc, FPS, RGB_shape)
            FIR_video = cv2.VideoWriter(FIR_fp, fourcc, FPS, FIR_shape)
    # RGB only
    elif 'STC_SCS312POE' in models:
        RGB_cam = h.create({'model': 'STC_SCS312POE'})
        setup_RGBcam(RGB_cam.remote_device.node_map)
        RGB_cam.start()
        if debug is not True:
            make_dirs(folder)
            RGB_video = cv2.VideoWriter(RGB_fp, fourcc, FPS, RGB_shape)
    # FIR only
    elif 'FLIR AX5' in models:
        FIR_cam = h.create({'model': 'FLIR AX5'})
        setup_FIRcam(FIR_cam.remote_device.node_map)
        FIR_cam.start()
        if debug is not True:
            make_dirs(folder)
            FIR_video = cv2.VideoWriter(FIR_fp, fourcc, FPS, FIR_shape)
    # exception handling
    else:
        print('E: Cannot find any devices. Please check your connection and restart.')
        h.reset()
        return

    RGB = np.zeros((RGB_shape[1], RGB_shape[0], 3))
    FIR = np.zeros((FIR_shape[1], FIR_shape[0], 3))

    print('start')
    try:
        print()
        dt: float = 1.0  # processing time
        # RGB-FIR mode
        if 'STC_SCS312POE' in models and 'FLIR AX5' in models:
            for frame in count():
                start_time = time.time()
                if frame % 5 == 0:
                    print('\033[1A', end='')
                    print(f'processing... at {frame} frame / {1 / dt:.3f} FPS')
                FIR = get_camdata(FIR_cam, 'FIR')
                RGB = get_camdata(RGB_cam, 'RGB')
                if debug is not True:
                    RGB_video.write(RGB)
                    FIR_video.write(FIR)
                RGB = cv2.resize(RGB, (640, 512))
                if calib is True:
                    RGB = detect(RGB, False)
                    FIR = detect(FIR, True)
                concat = np.concatenate((RGB, FIR), axis=1)
                cv2.namedWindow('RGB-FIR')
                cv2.imshow('RGB-FIR', concat)
                dt = time.time() - start_time
                if cv2.waitKey(10) == ord('q'):
                    break
        # RGB only
        elif 'STC_SCS312POE' in models:
            for frame in count():
                start_time = time.time()
                if frame % 5 == 0:
                    print('\033[1A', end='')
                    print(f'processing... at {frame} frame / {1 / dt:.3f} FPS')
                RGB = get_camdata(RGB_cam, 'RGB')
                if debug is not True:
                    RGB_video.write(RGB)
                RGB = cv2.resize(RGB, dsize=None, fx=1/3, fy=1/3)
                if calib is True:
                    RGB = detect(RGB, False)
                cv2.namedWindow('RGB')
                cv2.imshow('RGB', RGB)
                dt = time.time() - start_time
                if cv2.waitKey(10) == ord('q'):
                    break
        # FIR only
        elif 'FLIR AX5' in models:
            for frame in count():
                start_time = time.time()
                if frame % 5 == 0:
                    print('\033[1A', end='')
                    print(f'processing... at {frame} frame / {1 / dt:.3f} FPS')
                FIR = get_camdata(FIR_cam, 'FIR')
                if debug is not True:
                    FIR_video.write(FIR)
                if calib is True:
                    FIR = detect(FIR, True)
                cv2.namedWindow('FIR')
                cv2.imshow('FIR', FIR)
                dt = time.time() - start_time
                if cv2.waitKey(10) == ord('q'):
                    break

    # exception handling
    except Exception as e:
        print(f'Error: {e}')

    # release all handlers
    finally:
        if 'STC_SCS312POE' in models and 'FLIR AX5' in models:
            RGB_cam.stop()
            RGB_cam.destroy()
            FIR_cam.stop()
            FIR_cam.destroy()
            if debug is not True:
                RGB_video.release()
                FIR_video.release()
        elif 'STC_SCS312POE' in models:
            RGB_cam.stop()
            RGB_cam.destroy()
            if debug is not True:
                RGB_video.release()
        elif 'FLIR AX5' in models:
            FIR_cam.stop()
            FIR_cam.destroy()
            if debug is not True:
                FIR_video.release()
        cv2.destroyAllWindows()
        print('fin')
        h.reset()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    os.system('PAUSE')
