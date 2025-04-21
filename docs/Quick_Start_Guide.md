# Project Wannabe & KoboldCpp クイックアクセスガイド (Windows 向け)

## 1. はじめに

このガイドは、小説執筆支援アプリ `Project Wannabe` と、そのバックエンドとして動作する AI エンジン `KoboldCpp` を Windows 環境にセットアップし、連携させて動作確認を行うまでの手順を説明します。

## 2. 前提条件

*   **Python のインストール:** Python 3.9 以上が必要です。インストールされていない場合は、[Python 公式サイト](https://www.python.org/) からダウンロードしてインストールしてください。（インストール時に「Add Python to PATH」にチェックを入れることを推奨します。）
*   **Git のインストール:** `Project Wannabe` のソースコードを取得するために Git が必要です。インストールされていない場合は、[Git for Windows](https://gitforwindows.org/) からダウンロードしてインストールしてください。

## 3. KoboldCpp のセットアップ

### (1) KoboldCpp 本体のダウンロード

1.  [KoboldCpp GitHub Releases](https://github.com/LostRuins/koboldcpp/releases/latest) にアクセスします。
2.  最新リリースの `Assets` セクションから `koboldcpp.exe` をダウンロードします。
3.  ダウンロードした `koboldcpp.exe` を、分かりやすい場所（例: `C:\KoboldCpp` など、**スペースを含まないパス**を推奨）に保存します。

### (2) AI モデルファイルのダウンロード

1.  `Project Wannabe` が推奨する `wanabi 24B` モデル（GGUF 形式）をダウンロードします。
    *   **[wanabi 24B モデルのダウンロードリンクをここに記載]** *(現在リンクはありません。別途入手してください)*
    *   *代替案:* もし上記モデルが入手できない場合や、他のモデルを試したい場合は、[Hugging Face](https://huggingface.co/) で "GGUF" と検索し、 `.gguf` 形式のファイルを探します。KoboldCpp README 推奨モデル例: [Tiefighter 13B (Q4_K_S)](https://huggingface.co/KoboldAI/LLaMA2-13B-Tiefighter-GGUF/resolve/main/LLaMA2-13B-Tiefighter.Q4_K_S.gguf)
2.  ダウンロードした `.gguf` ファイルを、`koboldcpp.exe` と同じフォルダ、または分かりやすい場所に保存します。

### (3) KoboldCpp の起動とモデルロード

1.  保存した `koboldcpp.exe` をダブルクリックして実行します。
2.  GUI が表示されたら、「Quick access」セクションの「Browse」ボタンをクリックし、手順 (2) でダウンロードした `.gguf` モデルファイルを選択します。
3.  **(推奨) GPU 設定:**
    *   **NVIDIA GPU の場合:**
        *   「Use CuBLAS」にチェックを入れます。
        *   「GPU Layers」の項目に、GPU にオフロードしたいレイヤー数を数字で入力します。(VRAM 容量に応じて調整してください。一般的に、数値が大きいほど高速になりますが、VRAM を超えるとエラーになります。VRAM 16GB 以上あれば `999` と入力して全レイヤーをオフロードできます。)
    *   **AMD/Intel GPU の場合:**
        *   「Use Vulkan」などのオプションを試してください。（環境によっては利用できない場合があります）
4.  **Context Size:** モデルが扱える文章の長さを設定します。使用するモデルや VRAM 容量に応じて調整してください。（例: `4096`, `8192` モデルの最大コンテキストは`32000`です。）
5.  **KV Cache:** 「Tokens」セクションにある「KV cache」を「8bit」に設定することを推奨します。(4bit が最軽量ですが、品質低下が大きいとされています。)
6.  設定が完了したら、「Launch」ボタンをクリックします。
7.  コンソールウィンドウが表示され、モデルのロードが始まります。しばらく待つと、コンソールに `KoboldAI API server listening at: http://localhost:5001` (または設定したポート番号) のようなメッセージが表示されれば起動成功です。
8.  **注意:** このコンソールウィンドウは KoboldCpp が動作している間、**閉じないでください。**

## 4. Project Wannabe のセットアップ

### (1) ソースコードのダウンロード (クローン)

1.  コマンドプロンプトまたは PowerShell を開きます。
2.  `Project Wannabe` を配置したいディレクトリに移動します (例: `cd F:\Project-Wannabe` の親ディレクトリ)。**スペースを含まないパス**を推奨します。
3.  以下のコマンドを実行して、ソースコードをダウンロードします。
    ```bash
    git clone https://github.com/kawaii-justice/Project-Wannabe.git
    ```


### (2) プロジェクトディレクトリへの移動

1.  コマンドプロンプトまたは PowerShell で、`Project Wannabe` のディレクトリに移動します。
    ```bash
    cd F:\Project-Wannabe
    ```

### (3) 仮想環境の作成と有効化

1.  以下のコマンドを実行して、Python 仮想環境を作成し、有効化します。
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
2.  コマンドプロンプトの行頭に `(venv)` と表示されれば、仮想環境が有効になっています。

### (4) 依存ライブラリのインストール

1.  仮想環境が有効な状態で、以下のコマンドを実行して、必要なライブラリをインストールします。
    ```bash
    pip install -r requirements.txt
    ```

## 5. 連携と動作確認

### (1) KoboldCpp の起動確認

*   手順 3-(3) で起動した KoboldCpp のコンソールウィンドウが開いており、`listening at: http://localhost:5001` のようなメッセージが表示されていることを確認します。

### (2) Project Wannabe の起動

1.  `Project Wannabe` のディレクトリ (`F:\Project-Wannabe`) で、仮想環境が有効な状態 (行頭に `(venv)`) であることを確認します。
2.  以下のコマンドを実行して `Project Wannabe` を起動します。
    ```bash
    python main.py
    ```

### (3) Project Wannabe の設定

1.  `Project Wannabe` のウィンドウが表示されたら、メニューバーの `設定` > `KoboldCpp 設定...` を開きます。
2.  「Port」が KoboldCpp の起動時に表示されたポート番号 (デフォルト: `5001`) と一致していることを確認し、必要であれば修正して「OK」をクリックします。

### (4) 簡単な動作確認

1.  `Project Wannabe` の左上の本文エリアに適当な文章（例: 「昔々あるところに」）を入力します。
2.  メニューバーの `生成` > `単発生成 (Ctrl+G)` をクリックします。
3.  左下の出力エリアに、AI が生成した続きの文章が表示されれば連携成功です。
