from harvesters.core import Harvester
from concurrent.futures import ThreadPoolExecutor
from itertools import count
import cv2
import os
import numpy as np


# ユーザパラメータ
RGB_shape = (2048, 1536)  # (w,h)
FIR_shape = (640, 512)
FPS = 30
debug = False
SingleMode = True
save_folder = r'./out'
cti = 'mvGenTLProducer.cti'


# --------------------------------------------------
# 現在時刻を取得
# --------------------------------------------------
def get_datetime():
    import datetime
    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, 'JST')
    now = datetime.datetime.now(JST)
    return now.strftime('%Y%m%d_%H%M')


# --------------------------------------------------
# 絶対パス to 相対パス (exe側かtempフォルダか指定)
# --------------------------------------------------
def rel2abs_path(filename, attr):
    import sys
    if attr == 'temp':  # 展開先フォルダと同階層
        datadir = os.path.dirname(__file__)
    elif attr == 'exe':  # exeファイルと同階層の絶対パス
        datadir = os.path.dirname(sys.argv[0])
    else:
        raise print(f'E: 相対パスの引数ミス [{attr}]')
    return os.path.join(datadir, filename)


# --------------------------------------------------
# 保存フォルダを作る
# --------------------------------------------------
def make_dirs(folder):
    os.makedirs(os.path.join(folder, 'RGB_raw'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'RGB'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'FIR'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'concat'), exist_ok=True)


# --------------------------------------------------
# GigEのバイナリデータをcv2画像にして取得
# --------------------------------------------------
def get_camdata(cam, flag):
    with cam.fetch() as buffer:
        # print(cam.statistics.fps)
        component = buffer.payload.components[0]
        width = component.width
        height = component.height
        data = component.data.reshape(height, width)
        if flag == 'RGB':
            img = cv2.cvtColor(data, cv2.COLOR_BayerBG2RGB)
        elif flag == 'FIR':
            img = cv2.cvtColor(data, cv2.COLOR_GRAY2RGB)
        return img


def main():
    # Connect to Camera
    h = Harvester()
    h.add_file(os.path.join(os.getenv('GENICAM_GENTL64_PATH'), cti))

    h.update()
    models = [d.property_dict.get('model') for d in h.device_info_list]
    print(f'認識したデバイス{models}')

    # Setup folders and files
    folder = os.path.join(save_folder, get_datetime())
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    RGB_fp = os.path.join(folder, 'RGB.mp4')
    FIR_fp = os.path.join(folder, 'FIR.mp4')
    RGB_FIR_fp = os.path.join(folder, 'RGB-FIR.mp4')

    # Select a mode
    if 'STC_SCS312POE' in models and 'FLIR AX5' in models:  # RGB-FIR
        RGB_cam = h.create({'model': 'STC_SCS312POE'})
        FIR_cam = h.create({'model': 'FLIR AX5'})
        RGB_cam.start()
        RGB_config = RGB_cam.remote_device.node_map
        RGB_config.TriggerMode.value = 'Off'
        RGB_config.TriggerMode.value = 'On'
        RGB_config.TriggerSource.value = 'Line0'
        RGB_config.TriggerActivation.value = 'LevelHigh'
        RGB_config.LineDebounceTime.value = 0
        RGB_config.ExposureAuto.value = 'Continuous'
        RGB_config.GainAuto.value = 'Continuous'
        RGB_config.TargetBrightness.value = 128
        RGB_config.AGCRange.value = 208

        FIR_cam.start()
        FIR_config = FIR_cam.remote_device.node_map
        FIR_config.SyncMode.value = 'SelfSyncMaster'
        FIR_config.AcquisitionMode.value = 'Continuous'

        make_dirs(folder)
        RGBFIR_video = cv2.VideoWriter(
            RGB_FIR_fp, fourcc, FPS, (FIR_shape[0]*2, FIR_shape[1]))

    elif 'STC_SCS312POE' in models:  # RGB only
        RGB_cam = h.create({'model': 'STC_SCS312POE'})
        RGB_cam.start()
        RGB_config = RGB_cam.remote_device.node_map
        RGB_config.TriggerMode.value = 'Off'
        RGB_config.ExposureAuto.value = 'Continuous'
        RGB_config.GainAuto.value = 'Continuous'
        RGB_config.TargetBrightness.value = 128
        RGB_config.AGCRange.value = 208
        make_dirs(folder)
        RGB_video = cv2.VideoWriter(RGB_fp, fourcc, FPS, RGB_shape)

    elif 'FLIR AX5' in models:   # FIR only
        FIR_cam = h.create({'model': 'FLIR AX5'})
        FIR_cam.start()
        FIR_config = FIR_cam.remote_device.node_map
        FIR_config.SyncMode.value = 'Disabled'
        FIR_config.AcquisitionMode.value = 'Continuous'
        make_dirs(folder)
        FIR_video = cv2.VideoWriter(FIR_fp, fourcc, FPS, FIR_shape)

    else:  # 例外処理
        print('E: Cannot find any devices. Please check your connection and restart')
        return

    RGB = np.zeros((RGB_shape[1], RGB_shape[0], 3))
    FIR = np.zeros((FIR_shape[1], FIR_shape[0], 3))

    print('start')
    try:
        if 'STC_SCS312POE' in models and 'FLIR AX5' in models:  # RGB-FIR
            for frame in count():
                if frame % 100 == 0 and frame != 0:
                    print(f'processing... {frame}')
                    print(RGB_cam.statistics.fps)
                RGB = get_camdata(RGB_cam, 'RGB')
                FIR = get_camdata(FIR_cam, 'FIR')
                concat = np.concatenate(
                    (cv2.resize(RGB, (640, 512)), FIR), axis=1)
                RGBFIR_video.write(concat)
                cv2.namedWindow('RGB-FIR')
                cv2.imshow('RGB-FIR', concat)
                if cv2.waitKey(10) == ord('q'):
                    break

        elif 'STC_SCS312POE' in models:  # RGBのみ
            for frame in count():
                if frame % 100 == 0 and frame != 0:
                    print(f'processing... {frame}')
                    print(RGB_cam.statistics.fps)
                RGB = get_camdata(RGB_cam, 'RGB')
                with ThreadPoolExecutor(max_workers=2, thread_name_prefix="thread") as executor:
                    executor.submit(RGB_video.write, RGB)
                    executor.submit(cv2.imshow('RGB', RGB))
                if cv2.waitKey(10) == ord('q'):
                    break
                if debug and frame > 300:
                    break

        elif 'FLIR AX5' in models:  # FIRのみ
            for frame in count():
                if frame % 100 == 0 and frame != 0:
                    print(f'processing... {frame}')
                    print(FIR_cam.statistics.fps)
                FIR = get_camdata(FIR_cam, 'FIR')
                cv2.namedWindow('FIR')
                with ThreadPoolExecutor(max_workers=2, thread_name_prefix="thread") as executor:
                    executor.submit(FIR_video.write, FIR)
                    executor.submit(cv2.imshow('FIR', FIR))
                if cv2.waitKey(10) == ord('q'):
                    break

    except Exception as e:  # 例外処理
        print(f'Error: {e}')

    finally:  # カメラやファイルをリリース
        if 'STC_SCS312POE' in models and 'FLIR AX5' in models:  # RGB-FIR
            RGB_cam.stop()
            RGB_cam.destroy()
            FIR_cam.stop()
            FIR_cam.destroy()
            RGB_video.release()
            FIR_video.release()
        elif 'STC_SCS312POE' in models:
            RGB_cam.stop()
            RGB_cam.destroy()
            RGB_video.release()
        elif 'FLIR AX5' in models:
            FIR_cam.stop()
            FIR_cam.destroy()
            FIR_video.release()
        cv2.destroyAllWindows()
        print('fin')
        h.reset()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
