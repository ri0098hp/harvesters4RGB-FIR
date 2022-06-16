from harvesters.core import Harvester
import cv2
import os
import numpy as np


# ユーザパラメータ
RGB_shape = (2048, 1536)
IR_shape = (640, 512)
FPS = 30
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
    os.makedirs(os.path.join(folder, 'IR'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'concat'), exist_ok=True)


# --------------------------------------------------
# GigEのバッファから必要なバイナリデータを取得
# --------------------------------------------------
def get_data(buffer):
    component = buffer.payload.components[0]
    width = component.width
    height = component.height
    data = component.data.reshape(height, width)
    return data


def main():
    # カメラと接続
    h = Harvester()
    h.add_file(os.path.join(os.getenv('GENICAM_GENTL64_PATH'), cti))
    h.update()
    print('認識したデバイス')
    for device in h.device_info_list:
        print(device.property_dict.get('model'))

    # モードを選択
    while True:
        flag = input()
        if flag == '0':  # RGB-FIR
            RGB_cam = h.create({'model': 'STC_SCS312POE'})
            FIR_cam = h.create({'model': 'FLIR AX5'})
            RGB_cam.start()
            FIR_cam.start()
            break
        elif flag == 'RGB':  # RGBカメラのみ
            RGB_cam = h.create({'model': 'STC_SCS312POE'})
            RGB_cam.start()
            break
        elif flag == 'FIR':   # FIRカメラのみ
            FIR_cam = h.create({'model': 'FLIR AX5'})
            FIR_cam.start()
            break
        elif '&' in flag:
            None
        else:
            print('Invalid Parameter. Please input "0, RGB, FIR".')

    # フォルダを作成
    folder = os.path.join(save_folder, get_datetime())
    make_dirs(folder)

    # ビデオファイルを設定
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fp = os.path.join(folder, 'RGB.mp4')
    RGB_video = cv2.VideoWriter(fp, fourcc, FPS, RGB_shape)
    fp = os.path.join(folder, 'FIR.mp4')
    FIR_video = cv2.VideoWriter(fp, fourcc, FPS, IR_shape)
    fp = os.path.join(folder, 'RGB-FIR.mp4')
    RGBFIR_video = cv2.VideoWriter(
        fp, fourcc, FPS, (IR_shape[0]*2, IR_shape[1]))

    try:
        frame = 0
        RGB = None
        FIR = None
        print('start')
        while True:
            if frame % 100 == 0 and frame != 0:
                print(f'processing... {frame}')

            if flag == '0':  # RGB-FIR
                with RGB_cam.fetch() as buffer:
                    data = get_data(buffer)
                    print(RGB_cam.statistics.fps)
                    RGB = cv2.cvtColor(data, cv2.COLOR_BayerBG2RGB)

                with FIR_cam.fetch() as buffer:
                    data = get_data(buffer)
                    print(FIR_cam.statistics.fps)
                    FIR = cv2.cvtColor(data, cv2.COLOR_GRAY2RGB)

                concat = np.concatenate(
                    (cv2.resize(RGB, (640, 512)), FIR), axis=1)
                RGBFIR_video.write(concat)
                cv2.namedWindow('RGB-FIR')
                cv2.imshow('RGB-FIR', concat)

            elif flag == 'RGB':  # RGBのみ
                with RGB_cam.fetch() as buffer:
                    data = get_data(buffer)
                    print(RGB_cam.statistics.fps)
                    RGB = cv2.cvtColor(data, cv2.COLOR_BayerBG2RGB)
                    RGB = calibration(RGB)
                    cv2.namedWindow('RGB')
                    RGB_video.write(RGB)
                    cv2.imshow('RGB', RGB)

            elif flag == 'FIR':  # FIRのみ
                with FIR_cam.fetch() as buffer:
                    data = get_data(buffer)
                    print(FIR_cam.statistics.fps)
                    FIR = cv2.cvtColor(data, cv2.COLOR_GRAY2RGB)
                    FIR_video.write(FIR)
                    cv2.namedWindow('FIR')
                    cv2.imshow('FIR', FIR)

            if cv2.waitKey(10) == ord('q'):  # 終了
                break
            frame = frame + 1

    except Exception as e:  # 例外処理
        print(f'Error: {e}')

    finally:  # カメラやファイルをリリース
        if flag == '0':  # RGB-FIR
            RGB_cam.stop()
            RGB_cam.destroy()
            FIR_cam.stop()
            FIR_cam.destroy()
            RGB_video.release()
            FIR_video.release()
        elif flag == 'RGB':  # RGBカメラのみ
            RGB_cam.stop()
            RGB_cam.destroy()
            RGB_video.release()
        elif flag == 'FIR':   # FIRカメラのみ
            FIR_cam.stop()
            FIR_cam.destroy()
            FIR_video.release()
        cv2.destroyAllWindows()
        print('fin')
        h.reset()


# --------------------------------------------------
# RGBカメラでパターン検出
# --------------------------------------------------
def calibration(img):
    para = {'width': 1500,
            'col': 6,  # 列(連続何個) 10
            'row': 4,  # 行(段数何個) 23
            'sym': 1  # 1:円形対称パターン, 2:円形非対称パターン
            }

    h, w = img.shape[:2]
    width = para['width']
    height = round(h * (width / w))
    if width < w:
        img = cv2.resize(img, (width, height))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findCirclesGrid(
        gray, (para['col'], para['row']), None, flags=para['sym'])

    if ret is True:  # 検出できた場合描画
        img = cv2.drawChessboardCorners(
            img, (para['col'], para['row']), corners, ret)
    img = cv2.resize(img, (w, h))
    return img


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
