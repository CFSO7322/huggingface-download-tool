# 导入 tkinter 库，用于创建图形用户界面
import tkinter as tk
# 从 tkinter 中导入 messagebox 模块，用于显示消息框
from tkinter import messagebox, filedialog
# 从 tkinter 中导入 filedialog 模块，用于选择文件夹
from huggingface_hub import snapshot_download, list_repo_files
from threading import Thread, Lock
import os
import sys
import ctypes
import subprocess
# 导入 shlex 模块，用于分割命令字符串
import shlex
import psutil  # 导入 psutil 库
# 定义一个锁来保证线程安全
stop_flag_lock = Lock()
# 定义一个全局变量来保存当前运行的进程
current_process = None

# 定义一个全局标志位，用于控制线程的运行
stop_flag = False
# 定义一个全局标志位，用于判断是否是用户主动关闭窗口
user_closed_window = False
# 定义一个全局变量来保存所选文件列表
selected_files_global = []

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
    status_label.config(text="正在准备选择文件……")

    def download():
        try:
            all_files = list_repo_files(repo_id=model_url)
            select_window = create_file_selection_window(all_files, model_url, local_dir)
            root.after(0, select_window.mainloop)  # 在主线程中运行窗口
        except Exception as e:
            root.after(0, lambda e=e: show_error(f"下载失败: {str(e)}"))  # 显式传递异常对象

    download_thread = Thread(target=download)
    # 设置线程为守护线程
    download_thread.daemon = True
    download_thread.start()

    # 下载开始后，将下载按钮变为暂停按钮
    button_download.config(text="暂停", command=pause_download)

# 定义暂停下载的函数
def pause_download():
    global stop_flag, current_process
    with stop_flag_lock:
        stop_flag = True
    if current_process:
        try:
            current_process.terminate()
            # 等待一段时间，看进程是否终止
            current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # 如果超时，强制杀死进程
            try:
                current_process.kill()
            except Exception as e:
                print(f"强制杀死进程时出现异常: {e}")
        except Exception as e:
            print(f"终止进程时出现异常: {e}")
    # 暂停后，将暂停按钮变为继续下载按钮
    button_download.config(text="继续下载", command=resume_download)

# 定义继续下载的函数
def resume_download():
    global stop_flag
    with stop_flag_lock:
        stop_flag = False
    # 继续下载后，将继续下载按钮变为暂停按钮
    button_download.config(text="暂停", command=pause_download)
    # 这里需要重新启动下载逻辑，可根据实际情况调整
    model_url = entry_url.get()
    local_dir = entry_dir.get()
    global selected_files_global
    selected_files = selected_files_global
    def inner_download():
        try:
            download_with_progress(model_url, local_dir, selected_files)
            root.after(0, finish_download)
        except Exception as e:
            root.after(0, lambda e=e: show_error(f"下载失败: {str(e)}"))
    download_thread = Thread(target=inner_download)
    download_thread.daemon = True
    download_thread.start()

# 创建一个按钮，点击时调用 download_model 函数
button_download = tk.Button(root, text="下载", command=download_model)
button_download.pack()

def download_with_progress(repo_id, local_dir, files):
    global stop_flag, current_process
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
        print(f"执行命令: {command}")  # 打印执行的命令
        current_process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

        while True:
            with stop_flag_lock:
                if stop_flag:
                    print("检测到暂停标志，终止下载进程")
                    try:
                        current_process.terminate()
                        # 等待一段时间，看进程是否终止
                        current_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # 如果超时，强制杀死进程
                        current_process.kill()
                    break
            output = current_process.stdout.readline()
            if output == '' and current_process.poll() is not None:
                break
            if output:
                print(output.strip())
        _, stderr = current_process.communicate()
        if stderr:
            print(f"错误信息: {stderr.strip()}")
        else:
            print("下载进程正常结束")

    except Exception as e:
        print(f"下载过程中出现异常: {str(e)}")  # 打印异常信息
        root.after(0, lambda e=e: show_error(f"下载失败: {str(e)}"))

# 定义显示错误信息的函数
def show_error(message):
    messagebox.showerror("错误", message)

# 定义下载完成后的处理函数
def finish_download():
    global stop_flag
    # 检查 stop_flag 确保是下载完成而不是暂停
    if not user_closed_window and not stop_flag:
        root.after(0, lambda: status_label.config(text="下载完成"))
        local_dir = entry_dir.get()
        if local_dir and os.path.exists(local_dir):
            os.startfile(local_dir)
        # 添加关闭窗口的代码
        root.after(1000, root.destroy)  # 等待1秒后关闭窗口

def create_file_selection_window(files, model_url, local_dir):
    select_window = tk.Toplevel(root)
    select_window.title("选择要下载的文件")
    selected_files = []
    vars = []

    # 创建一个框架用于放置滚动条和复选框
    frame = tk.Frame(select_window)
    frame.pack(fill=tk.BOTH, expand=True)

    # 创建垂直滚动条
    scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 创建一个画布用于放置复选框
    canvas = tk.Canvas(frame, yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=canvas.yview)

    # 创建一个框架用于放置复选框
    checkbox_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=checkbox_frame, anchor=tk.NW)

    def select_all():
        for var in vars:
            var.set(True)

    def deselect_all():
        for var in vars:
            var.set(False)

    # 创建全选和取消全选按钮
    select_all_button = tk.Button(select_window, text="全选", command=select_all)
    select_all_button.pack()
    deselect_all_button = tk.Button(select_window, text="取消全选", command=deselect_all)
    deselect_all_button.pack()

    def select_files():
        nonlocal selected_files
        selected_files = [file for i, file in enumerate(files) if vars[i].get()]
        global selected_files_global
        selected_files_global = selected_files  # 保存所选文件列表到全局变量
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
            root.after(0, lambda: status_label.config(text=""))

    for i, file in enumerate(files):
        var = tk.BooleanVar()
        vars.append(var)
        # 让复选框左对齐
        checkbox = tk.Checkbutton(checkbox_frame, text=file, variable=var)
        checkbox.pack(anchor=tk.W)  
    # 更新画布滚动区域
    checkbox_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox(tk.ALL))
    # 绑定鼠标滚轮事件到画布
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", on_mousewheel)
    tk.Button(select_window, text="确定", command=select_files).pack()
    return select_window
# 定义窗口关闭时的处理函数
def on_window_close():
    global stop_flag, current_process, user_closed_window
    user_closed_window = True
    with stop_flag_lock:
        stop_flag = True
    if current_process:
        try:
            current_process.terminate()
            # 等待一段时间，看进程是否终止
            current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # 如果超时，强制杀死进程
            current_process.kill()
    # 确保窗口销毁逻辑只执行一次
    if root.winfo_exists():
        root.destroy()

# 绑定窗口关闭事件
root.protocol("WM_DELETE_WINDOW", on_window_close)

# 启动主窗口的事件循环，使窗口保持显示状态
root.mainloop()
