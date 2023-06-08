# Harvesters for RGB-FIR Camera Capture

## Demo

<https://github.com/ri0098hp/harvesters4RGB-FIR/assets/104181368/cc174e1b-9ae7-4657-be90-97f1039afc9c>

## Outline

- [Harvesters for RGB-FIR Camera Capture](#harvesters-for-rgb-fir-camera-capture)
  - [Demo](#demo)
  - [Outline](#outline)
  - [Features](#features)
  - [Requirement](#requirement)
  - [Todo List](#todo-list)
  - [Installation](#installation)
    - [1.ドライバを含むSDKのインストール](#1ドライバを含むsdkのインストール)
    - [2. ドライバの設定 (USB to Etherを用いている場合のみ)](#2-ドライバの設定-usb-to-etherを用いている場合のみ)
    - [3. ffmpegのインストール](#3-ffmpegのインストール)
    - [4. ソフト本体のダウンロード](#4-ソフト本体のダウンロード)
  - [Usage](#usage)
    - [カメラの録画 (RGB-FIRCamera.py)](#カメラの録画-rgb-fircamerapy)
    - [録画した動画を加工 (RGB-FIRTools.py)](#録画した動画を加工-rgb-firtoolspy)
  - [Build](#build)
    - [1. Python環境を構築](#1-python環境を構築)
    - [2. セットアップツールの実行](#2-セットアップツールの実行)
    - [3. Pythonをgccでビルドする](#3-pythonをgccでビルドする)
  - [補足](#補足)
    - [ソフトウェアのパラメータ](#ソフトウェアのパラメータ)
    - [カメラ概要](#カメラ概要)
  - [以下引用](#以下引用)

## Features

RGB-FIRカメラの録画とデータセット用の画像の抽出を行う.

## Requirement

[Pipfile](Pipfile) 参照

## Todo List

- Python 3.10
  - harvesters
  - opencv-python
  - 場合によっては[YOLOv8-4ch](https://github.com/ri0098hp/YOLOv8-4ch)のwhlが必要
- GenTL Producer (Driver等を含むSDK)
- GenICam対応カメラ (GigEまたはUSB3対応カメラ)

## Installation

### 1.ドライバを含むSDKのインストール

既に導入済みなら飛ばしても良い.  
今回はMATRIX VISIONの "mvIMPACT_Acquire" をつかう. [ここ](http://static.matrix-vision.com/mvIMPACT_Acquire/) から最新版を選択し, OSにあった mvGenTL_Acquire をインストールする.  
動作確認済みなのは2.46.2で `mvGenTL_Acquire-x86_64-2.46.2.exe`と`mvGenTL_Acquire-ARM64_gnu-2.46.2.tgz`.  

### 2. ドライバの設定 (USB to Etherを用いている場合のみ)

デバイスマネージャを開きGigEドライバの設定画面でジャンボフレームを設定. 基本的には大きめの値を指定.
RGB, FIRどちらも設定しておくとよい.

### 3. ffmpegのインストール

ffmpegは [ここ](https://ffmpeg.org/download.html) からダウンロードし、適当な場所に保存し環境変数を通しておく.

### 4. ソフト本体のダウンロード

[release](/releases/latest) からzipをダウンロードし適当なフォルダに解凍する. (Pythonでビルドする場合はgit cloneから)

## Usage

### カメラの録画 (RGB-FIRCamera.py)

`RGB-FIRCamera.exe` をダブルクリックで起動する.
実行後, 認識しているカメラのモデル名一覧が出るので確認. ウィンドウが表示される (されない場合はタスクバーを確認してアクティブに) のでそのまま撮影.  
終了する場合はカメラウィンドウをアクティブにした状態で「q」を入力.  
[setting.yaml](setting.yaml) で保存場所を参照しファイルが保存される. その他のオプションは [補足](#ソフトウェアのパラメータ) の表を参照.

| :exclamation:  注意  :exclamation:                                                              |
| ----------------------------------------------------------------------------------------------- |
| GenICamのライブラリファイルであるctiが見つからない場合は環境変数の GENICAM_GENTL64_PATH を参照. |

### 録画した動画を加工 (RGB-FIRTools.py)

[setting.yaml](setting.yaml) で実行する内容を選択する. その後`RGB-FIRTools.exe` をダブルクリックで起動すると選択可能なフォルダが一覧で表示されるのでその中から選択し入力する. すると各フォルダにファイルが生成される. オプションは [補足](#補足) の表を参照.

もし動画をフル (29.970 FPS) で静止画に変換したい場合はPowerShellにて次のコマンドを実施する.

```bash
ffmpeg -i FIR.mp4 -qscale 0 -start_number 1 FIR/%d.jpg
ffmpeg -i RGB_raw.mp4 -qscale 0 -start_number 1 RGB_raw/%d.jpg
```

## Build

### 1. Python環境を構築

仮想環境にてインストール.  Pythonのバージョンは3.7推奨. Pyenv+PipenvまたはPyenv+Poetry推奨.
[参照](https://zenn.dev/hironobuu/articles/663ce389370210)

```bash
pipenv install --dev
```

これらで導入する場合は仮想環境に入った状態で以降を実行すること.

```bash
pipenv shell
```

### 2. セットアップツールの実行

必要ライブラリを導入したら `setup.py` を実行. 詳細は以下の公式ドキュメント [Tutorials](#tutorials) 参照.

```bash
python setup.py install
```

| :exclamation:  注意  :exclamation:                                                                                    |
| --------------------------------------------------------------------------------------------------------------------- |
| JetsonなどARMアーキテクチャの場合は特殊インストールが必要. [[参考](https://github.com/genicam/harvesters/issues/254)] |

### 3. Pythonをgccでビルドする

nuitkaを用いてPythonを必要としないバイナリファイルをビルドすることができる.

```ps
nuitka --onefile .\RGB-FIRCamera.py
```

```ps
nuitka --onefile --nofollow-import-to=harvesters --nofollow-import-to=genicam .\RGB-FIRTools.py
```

## 補足

### ソフトウェアのパラメータ

[setting.ini](setting.ini)のパラメータについて (ただしboolの場合は [0,1] で選択)
| RGB-FIRCmamera | input | about                                                                         |
| -------------- | ----- | ----------------------------------------------------------------------------- |
| debug          | bool  | 1のとき画面表示のみでフォルダやファイルを生成しない                           |
| calib          | bool  | 1のときキャリブレーション用の丸型マーカーを検知し表示                         |
| sep_mode       | bool  | 1のとき同期信号を用いずにFPS指定による撮影を行う                              |
| save_folder    | str   | 文字列でexeからの相対パスを示す. ここで指定したフォルダ下にファイルを生成する |

| RGB-FIRTools | type  | about                                                                                      |
| ------------ | ----- | ------------------------------------------------------------------------------------------ |
| mp4tojpg     | float | 0以外のときRGB_raw.mp4とFIR.mp4から設定値のFPSで連番画像を生成する (RGB_rawとFIRフォルダ)  |
| crop         | bool  | 1のときRGB_rawフォルダの画像をFIRの大きさに縮小しクロップする (RGB_cropフォルダ)           |
| pers         | bool  | 射影変換による簡易の位置合わせを行う (RGBフォルダ)                                         |
| homo         | str   | 0以外のときRGB_rawフォルダの画像に指定したホモグラフィ行列npyを適応する (RGB_homoフォルダ) |
| merge        | bool  | 1のときRGBフォルダとFIRフォルダの連番画像を結合し一枚の画像にする (concatフォルダ)         |
| fuse         | str   | 指定したフォルダのRGB画像とFIRフォルダの画像を加算合成する (fusedフォルダ)                 |

### カメラ概要

RGBカメラ: [STC_SCS312POE](docs\STC_SCS312POE.pdf)
FIRカメラ: [FLIR_AX5](docs\FLIR_AX5.pdf)
アタッチメント: [HR10A-7R-6SC](docs/HR10A-7R-6SC.pdf)
カシメ具: [HR12-SC-111](docs/HR12-SC-111.pdf)

## 以下引用
>
> ## Tutorials
>
> Are you ready to start working with Harvester? You can learn some more topics
> on these pages:
>
> - [INSTALL.rst](docs/INSTALL.rst) : Learn how to install Harvester and its prerequisites.
> - [TUTORIAL.rst](docs/TUTORIAL.rst) : Learn how Harvester can be used on  a typical image acquisition workflow.
>
> ## Links
>
>| Name              | URL                                          |
>| ----------------- | -------------------------------------------- |
>| Documentation     | <https://harvesters.readthedocs.io/en/latest/> |
>| Issue tracker     | <https://github.com/genicam/harvesters/issues> |
>| PyPI              | <https://pypi.org/project/harvesters/>         |
>| Source repository | <https://github.com/genicam/harvesters>        |
