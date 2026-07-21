# eCommerce Web：Windows 启动手册

本手册适用于 **Windows + Visual Studio Code**。

- 项目网页：<http://127.0.0.1:5000>
- 仓库：<https://github.com/universide/e-commerce-website>
- 停止服务：在正在运行网站的终端按 **Ctrl + C**

## 第一次下载和安装

在 VS Code 终端中依次执行：

~~~cmd
git clone https://github.com/universide/e-commerce-website.git
cd e-commerce-website
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python app.py
~~~

看到 “Running on http://127.0.0.1:5000” 后，在浏览器打开：

<http://127.0.0.1:5000>

终端一直处于运行状态是正常的，不要关闭。

## 以后再次启动

用 VS Code 打开 e-commerce-website 文件夹，在终端执行：

~~~cmd
.venv\Scripts\activate
python app.py
~~~

不需要每次重新创建 .venv 或重新安装依赖。

## 从 GitHub 获取更新

先按 **Ctrl + C** 停止网站，然后在项目根目录执行：

~~~cmd
git pull
~~~

如果 requirements-dev.txt 有变化，再执行：

~~~cmd
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
~~~

## 可选：运行自动测试

~~~cmd
.venv\Scripts\activate
pytest -q
~~~

## 常见问题

### 终端前面没有 (.venv)

重新执行：

~~~cmd
.venv\Scripts\activate
~~~

### 5000 端口被占用

Task Master 后端也使用 5000 端口。找到仍在运行的另一个项目终端，按 **Ctrl + C**，然后重新启动本项目。

### 本地数据在哪里

应用会在 instance 文件夹中生成本地 SQLite 数据库。它不会上传到 GitHub。