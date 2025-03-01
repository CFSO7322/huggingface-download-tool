# 导入 tkinter 库，用于创建图形用户界面
import tkinter as tk
# 从 tkinter 中导入 messagebox 模块，用于显示消息框
from tkinter import messagebox, filedialog
# 从 tkinter 中导入 filedialog 模块，用于选择文件夹
from huggingface_hub import snapshot_download, list_repo_files
from threading import Thread
import os
import sys
import ctypes
import subprocess
# 导入 shlex 模块，用于分割命令字符串
import shlex
import psutil  # 导入 psutil 库

# 定义一个全局标志位，用于控制线程的运行
stop_flag = False
# 定义一个全局标志位，用于判断是否是用户主动关闭窗口
user_closed_window = False

# 创建主窗口，必须放在所有GUI组件之前
root = tk.Tk()
root.title("HF模型下载工具")

# 主窗口居中
root.update_idletasks()
width = root.winfo_width()
height = root.winfo_height()
x = (root.winfo_screenwidth() // 2) - (width // 2)
y = (root.winfo_screenheight() // 2) - (height // 2)
root.geometry(f'+{x}+{y}')

# 定义选择文件夹的函数
def select_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        entry_dir.delete(0, tk.END)
        entry_dir.insert(0, folder_selected)

# 创建一个标签，显示“模型名称”
label_url = tk.Label(root, text="模型名称")
label_url.pack()

# 创建一个输入框，用于用户输入模型链接
entry_url = tk.Entry(root, width=50)
entry_url.insert(0, "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")  # 插入默认模型名称
entry_url.pack()

# 创建一个标签，显示“本地存储目录:”
label_dir = tk.Label(root, text="本地存储目录:")
label_dir.pack()

# 创建一个框架，用于放置输入框和选择文件夹按钮
frame_dir = tk.Frame(root)
frame_dir.pack()

# 创建一个输入框，用于用户输入本地存储目录
entry_dir = tk.Entry(frame_dir, width=40)
entry_dir.pack(side=tk.LEFT)

# 创建一个按钮，点击时调用 select_folder 函数
button_select_folder = tk.Button(frame_dir, text="选择文件夹", command=select_folder)
button_select_folder.pack(side=tk.LEFT)

# 创建一个用于显示下载状态的标签
status_label = tk.Label(root, text="")
status_label.pack()

# 创建一个变量来存储用户的源选择
source_var = tk.StringVar(root)
source_var.set("镜像地址")  # 默认选择镜像地址

# 创建单选框让用户选择源
radio_original = tk.Radiobutton(root, text="原始地址", variable=source_var, value="原始地址")
radio_original.pack()
radio_mirror = tk.Radiobutton(root, text="镜像地址", variable=source_var, value="镜像地址")
radio_mirror.pack()

# 定义下载模型的函数
def download_model():
    global stop_flag, user_closed_window
    stop_flag = False
    user_closed_window = False
    model_url = entry_url.get()
    local_dir = entry_dir.get()

    if not model_url or not local_dir:
        messagebox.showerror("错误", "请输入模型名称和本地存储目录")
        return
    # 显示正在下载提示
    status_label.config(text="正在下载……对不起，没有进度条！\n请关注目标文件夹内容及网络占用情况")

    def download():
        try:
            all_files = list_repo_files(repo_id=model_url)
            gguf_files = [f for f in all_files if f.endswith('.gguf')]
            if any(f.endswith('.safetensors') for f in all_files):
                download_with_progress(model_url, local_dir, all_files)
                root.after(0, finish_download)
            elif len(gguf_files) == 1:
                download_with_progress(model_url, local_dir, all_files)
                root.after(0, finish_download)
            elif len(gguf_files) > 1:
                select_window = create_file_selection_window(gguf_files, model_url, local_dir)
                root.after(0, select_window.mainloop)  # 在主线程中运行窗口

        except Exception as e:
            root.after(0, lambda e=e: show_error(f"下载失败: {str(e)}"))  # 显式传递异常对象

    download_thread = Thread(target=download)
    # 设置线程为守护线程
    download_thread.daemon = True
    download_thread.start()

# 创建一个按钮，点击时调用 download_model 函数
button_download = tk.Button(root, text="下载", command=download_model)
button_download.pack()

def download_with_progress(repo_id, local_dir, files):
    global stop_flag
    # 初始化允许下载的文件模式列表
    allow_patterns = []
    # 遍历文件列表，根据文件扩展名添加到允许模式列表
    for file in files:
        # 如果文件以 .gguf 结尾，添加带有通配符的模式
        if file.endswith('.gguf'):
            allow_patterns.append(f"*{file}")
        # 其他文件直接添加文件名
        else:
            allow_patterns.append(file)

    try:
        # 根据用户选择的源修改下载命令
        if source_var.get() == "镜像地址":
            # 修正镜像地址设置（使用根域名）
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        else:
            # 移除可能存在的镜像地址环境变量
            os.environ.pop('HF_ENDPOINT', None)

        command = f"huggingface-cli download {repo_id} --local-dir {local_dir} --include {' '.join(allow_patterns)} --resume-download"
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

        while True:
            if stop_flag:
                try:
                    process.terminate()
                    # 等待一段时间，看进程是否终止
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 如果超时，强制杀死进程
                    process.kill()
                break
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        _, stderr = process.communicate()
        if stderr:
            print(f"错误信息: {stderr.strip()}")

    except Exception as e:
        root.after(0, lambda e=e: show_error(f"下载失败: {str(e)}"))

# 定义显示错误信息的函数
def show_error(message):
    messagebox.showerror("错误", message)

# 定义下载完成后的处理函数
def finish_download():
    if not user_closed_window:
        root.after(0, lambda: status_label.config(text="下载完成"))
        local_dir = entry_dir.get()
        if local_dir and os.path.exists(local_dir):
            os.startfile(local_dir)
        # 添加关闭窗口的代码
        root.after(1000, root.destroy)  # 等待1秒后关闭窗口

def create_file_selection_window(gguf_files, model_url, local_dir):
    select_window = tk.Toplevel(root)
    select_window.title("选择要下载的文件")
    selected_files = []
    vars = []

    def select_files():
        nonlocal selected_files
        selected_files = [file for i, file in enumerate(gguf_files) if vars[i].get()]
        root.after(0, select_window.destroy)  # 在主线程销毁窗口
        if selected_files:
            # 选择完文件后显示下载提示
            root.after(0, lambda: status_label.config(text="正在下载……对不起，没有进度条！\n请关注目标文件夹内容及网络占用情况"))
            def inner_download():
                try:
                    download_with_progress(model_url, local_dir, selected_files)
                    root.after(0, finish_download)
                except Exception as e:
                    root.after(0, lambda e=e: show_error(f"下载失败: {str(e)}"))  # 显式传递异常对象
            download_thread = Thread(target=inner_download)
            # 设置线程为守护线程
            download_thread.daemon = True
            download_thread.start()
        else:
            messagebox.showinfo("提示", "未选择任何文件，取消下载。")
            root.after(0, lambda: status_label.config(""))

    for i, file in enumerate(gguf_files):
        var = tk.BooleanVar()
        vars.append(var)
        tk.Checkbutton(select_window, text=file, variable=var).pack()

    tk.Button(select_window, text="确定", command=select_files).pack()

    return select_window

# 定义关闭窗口时的处理函数
def on_closing():
    global stop_flag, user_closed_window
    stop_flag = True
    user_closed_window = True
    messagebox.showinfo("提示", "用户主动关闭")
    # 查找并终止 huggingface-cli.exe 进程
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'huggingface-cli.exe':
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                if isinstance(proc, psutil.TimeoutExpired):
                    proc.kill()
    # 等待一段时间，确保子进程有机会终止
    root.after(1000, root.destroy)

# 绑定关闭事件
root.protocol("WM_DELETE_WINDOW", on_closing)

# 启动主窗口的事件循环，使窗口保持显示状态
root.mainloop()
