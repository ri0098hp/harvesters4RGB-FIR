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
- [ ] cv2 writerをffmpegでpiped処理化 (qsv_hevcやcrf, vfr他)

# Features
RGB-FIRカメラの録画を行う.

# Requirement
[Pipfile](Pipfile) 参照
+ Python 3.7.9
  + harvesters
  + opencv-python
+ GenTL Producer (Driver等を含むSDK) 
+ GenICam対応カメラ (GigEまたはUSB3対応カメラ)


# Installation
既に導入済みなら飛ばしても良い.  
今回はMATRIX VISIONの "mvIMPACT_Acquire" をつかう. [ここ](http://static.matrix-vision.com/mvIMPACT_Acquire/) から最新版を選択し, OSにあった mvGenTL_Acquire をインストールする.  
動作確認済みなのは2.46.2で `mvGenTL_Acquire-x86_64-2.46.2.exe` .  
ドライバをインストール後releaseからzipをダウンロードし適当なフォルダに解凍する. (git cloneでも可能)

# Usage
## カメラの録画 (RGB-FIRCamera.py)
`RGB-FIRCamera.exe` をダブルクリックで起動する.
実行後, 認識しているカメラのモデル名一覧が出るので確認. ウィンドウが表示される (されない場合はタスクバーを確認してアクティブに) のでそのまま撮影.  
終了する場合はカメラウィンドウをアクティブにした状態で「q」を入力.  
[setting.ini](setting.ini) で保存場所を参照しファイルが保存される. その他のオプションは [補足](#補足) の表を参照.

| :exclamation:  注意  :exclamation:                                                              |
| ----------------------------------------------------------------------------------------------- |
| GenICamのライブラリファイルであるctiが見つからない場合は環境変数の GENICAM_GENTL64_PATH を参照. |


## 録画した動画を加工 (RGB-FIRTools.py)
[setting.ini](setting.ini) で実行する内容を選択する. その後`RGB-FIRTools.exe` をダブルクリックで起動すると選択可能なフォルダが一覧で表示されるのでその中から選択し入力する. すると各フォルダにファイルが生成される. オプションは [補足](#補足) の表を参照.
- 動画 to 画像ツール
- クロッピングツール
- キャリブレーションツール
- RGB-FIR画像結合ツール

# Build
## 1. Python環境を構築
仮想環境にてインストール.  Pythonのバージョンは3.7推奨. Pyenv+PipenvまたはPyenv+Poetry推奨. 
[参照](https://zenn.dev/hironobuu/articles/663ce389370210)
```bash
pipenv install --dev
```
これらで導入する場合は仮想環境に入った状態で以降を実行すること.
```bash
pipenv shell
```


## 2. セットアップツールの実行
必要ライブラリを導入したら `setup.py` を実行. 詳細は以下の公式ドキュメント [Tutorials](#tutorials) 参照.
```bash
python setup.py install
```

## 3. Pythonをgccでビルドする
nuitkaを用いてPythonを必要としないバイナリファイルをビルドすることができる.
```ps
nuitka --follow-imports --onefile --enable-plugin=numpy .\RGB-FIRCamera.py
```
```ps
nuitka --follow-imports --onefile --enable-plugin=numpy .\RGB-FIRTools.py
```

# 補足
[setting.ini](setting.ini)のパラメータについて (ただしboolの場合は [0,1] で選択)
| RGB-FIRCmamera | type | about                                                                         |
| -------------- | ---- | ----------------------------------------------------------------------------- |
| debug          | bool | 1のとき画面表示のみでフォルダやファイルを生成しない                           |
| calib          | bool | 1のときキャリブレーション用の丸型マーカーを検知し表示                         |
| sep_mode       | bool | 1のとき同期信号を用いずにFPS指定による撮影を行う                              |
| save_folder    | str  | 文字列でexeからの相対パスを示す. ここで指定したフォルダ下にファイルを生成する |

| RGB-FIRTools | type | about                                                                                       |
| ------------ | ---- | ------------------------------------------------------------------------------------------- |
| mp4tojpg     | bool | 1のときRGB_raw.mp4とFIR.mp4から連番画像を生成する (RGB_rawとFIRフォルダ)                    |
| crop         | bool | 1のときRGB_rawフォルダの画像をFIRの大きさに縮小しクロップする (RGB_cropフォルダ)            |
| calibrate    | bool | 1のときRGB_rawフォルダの画像を射影変換を用いて変換しFIRの大きさでクロップする (RGBフォルダ) |
| merge        | bool | 1のときRGBフォルダとFIRフォルダの連番画像を結合し一枚の画像にする (concatフォルダ)          |
| save_folder  | str  | RGB-FIRCameraと共通. ここで指定したフォルダ下にあるフォルダを再帰的に探索する               |



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
