Hugging Face模型下载工具

Hugging Face上的模型，有些可以通过命令快捷部署，比如ollama run hf.co/……这种。
但也有一些情况，我们需要手动下载。有时候会遗漏“config.json”这种小文件；一个一个下载的话更是麻烦；用控制台命令下载的方式不直观，不适合新手……
这个工具是我完全借助豆包和DeepSeek写出来的，我从未学过编程，只会反复PUA AI乙方！
实现了以下功能：
1.填入模型名称、选择存储路径后一键下载。（模型名称获取方式见附图）
2.可选清华镜像源和原始地址，默认使用镜像源，实测能跑满千兆宽带，很舒服。
3.对于有多个gguf文件的，允许用户选择其中一个或几个，避免一下子把好几个版本全都下载了。
尚未实现的功能：
进度条！死活搞不出来！有能力的亲可以帮帮忙……
奇怪的问题：
360有概率把它当病毒干掉，可它真不是病毒啊！
源文件放包里了，随便用，不需要署名。
B站UID:7663054  2025.3.1

Hugging Face Model Download Tool

Some models on Hugging Face can be quickly deployed through commands, such as ollama run hf.co/……
But there are also some situations where we need to manually download. Sometimes small files like 'config.json' may be overlooked; Downloading one by one is even more troublesome; Downloading using console commands is not intuitive and not suitable for beginners.
This tool was written entirely with the help of Doubao and DeepSeek. I have never learned programming and only know how to repeatedly PUA AI!
The following functions have been implemented:
1. Fill in the model name, select the storage path, and then download with one click. (The method of obtaining the model name is shown in the attached figure)
2. Optional Tsinghua image source and original address, default to using image source, tested to run full gigabit broadband, very comfortable.
3. For those with multiple gguf files, allow users to choose one or several of them to avoid downloading all versions at once.
Unrealized functions:
Unable to display progress bar! I can't figure it out! NICE bros please help.
Strange question:
Antivirus has a chance to kill it as a virus, but it's not really a virus!
The source file is in the package, feel free to use.
https://space.bilibili.com/7663054
2025.3.1
