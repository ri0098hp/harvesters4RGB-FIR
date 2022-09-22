Harvesters for RGB-FIR Camera Capture
====================================

# Demo
準備中

# Todo List
- [x] カメラのキャプチャ
- [x] バイナリアプリケーション化
- [x] 便利動画ツール
  - [x] 動画 to 画像ツール
  - [x] クロッピングツール
  - [x] キャリブレーションツール
- [] cv2 writerをffmpegでpiped処理化 (qsv_hevcやcrf, vfr他)

# Features
RGB-FIRカメラの録画を行う.

# Requirement
[Pipfile](Pipfile) 参照
+ Python 3.7.9
  + harvesters
  + ipython
  + opencv-python
+ GenTL Producer (Driver等を含むSDK) 
+ GenICam対応カメラ (GigEまたはUSB3対応カメラ)

# Installation
## 1. GenTL Producerを入れる
既に導入済みなら飛ばしても良い.  
今回はMATRIX VISIONの "mvIMPACT_Acquire" をつかう. [ここ](http://static.matrix-vision.com/mvIMPACT_Acquire/)から最新版を選択し, OSにあった mvGenTL_Acquire をインストールする.  
動作確認済みなのは2.46.2で `mvGenTL_Acquire-x86_64-2.46.2.exe` .

## 2. Python環境を構築
仮想環境にてインストール.  Pythonのバージョンは3.7推奨. PipenvやPoetry推奨. もしこれらで導入する場合は仮想環境に入った状態で以降を実行すること.  
仮想環境を用いない場合はpip実行可能な環境にて次のコマンド.
```bash
pip install -p
```

## 3. セットアップツールの実行
必要ライブラリを導入したら `setup.py` を実行. 詳細は以下の公式ドキュメント [Tutorials](#tutorials) 参照.
```bash
python setup.py install
```

# Usage
Pythonで `RGB-FIRCamera.py` を実行
```bash
python RGB-FIRCamera.py
```
実行後, 認識しているカメラのモデル名一覧が出るので確認. ウィンドウが表示される (されない場合はタスクバーを確認してアクティブに) のでそのまま撮影.  
終了する場合はカメラウィンドウをアクティブにした状態で「q」を入力. `./out/{日付}` にファイルが保存される.

| :exclamation:  注意                                                                             |
| ----------------------------------------------------------------------------------------------- |
| GenICamのライブラリファイルであるctiが見つからない場合は環境変数の GENICAM_GENTL64_PATH を参照. |

# 補足
動画から連番画像はffmpegを叩けばよい. 以下のコマンドをPowerShellで実行する. 
```ps
ffmpeg -i ./RGB.mp4 -q:v 1 -r 29.97 ./RGB_raw/%04d.jpg
ffmpeg -i ./FIR.mp4 -q:v 1 -r 29.97 ./FIR/%04d.jpg
```

exeファイル化するには
```ps
nuitka --follow-imports --onefile --enable-plugin=numpy .\RGB-FIRCamera.py
```
```ps
nuitka --follow-imports --onefile --enable-plugin=numpy .\RGB-FIRTools.py
```

ユーザパラメータ
| Name        | About                                                   |
| ----------- | ------------------------------------------------------- |
| RGB_shape   | RGBカメラの解像度                                       |
| IR_shape    | FIRカメラの解像度                                       |
| FPS         | 取得FPS値                                               |
| save_folder | 保存先のルートフォルダ                                  |
| cti         | ctiファイルの名前 (デフォルトは `mvGenTLProducer.cti` ) |
| debug       | 実行時にファイル・ディレクトリ生成を行わないかどうか    |
| calib       | キャリブレーションマーカー検出の行うか                  |
| sep_mode    | 同期信号を取るかどうか                                  |


カメラ概要
| Camera | Feature  | Num                |
| ------ | -------- | ------------------ |
| RGB    |          |                    |
|        | 焦点距離 | 0.1 17F 6mm        |
|        | 撮像素子 | H:7.06mm, W:5.29mm |
| FIR    |          |                    |
|        | 焦点距離 | 13 mm              |
|        | 撮像素子 | H: mm, W: mm       |


# 以下引用
>
># Tutorials
>Are you ready to start working with Harvester? You can learn some more topics
>on these pages:
>* [INSTALL.rst](docs/INSTALL.rst) : Learn how to install Harvester and its prerequisites.
>* [TUTORIAL.rst](docs/TUTORIAL.rst) : Learn how Harvester can be used on  a typical image acquisition workflow.
>
># Links
>| Name              | URL                                          |
>| ----------------- | -------------------------------------------- |
>| Documentation     | https://harvesters.readthedocs.io/en/latest/ |
>| Issue tracker     | https://github.com/genicam/harvesters/issues |
>| PyPI              | https://pypi.org/project/harvesters/         |
>| Source repository | https://github.com/genicam/harvesters        |
