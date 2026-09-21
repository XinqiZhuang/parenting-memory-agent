# 私有知识库与 GitHub 同步

日期：2026-09-21。安装本次更新后，飞书和网页共同检索随项目指南及家庭私有资料。

## 1. 安装代码

把 update_private_knowledge.py 上传至服务器 /home/admin/，在服务器终端执行：

```bash
sudo python3 /home/admin/update_private_knowledge.py
```

这是现有家庭功能的增量更新。更新器先核对已知版本，备份代码，暂停育儿服务，用临时假数据验证后再恢复服务；失败则恢复旧代码。不会改写真实宝宝档案、照片、凭证、作品集或 Nginx 配置。

若提示版本不一致，请保留输出核对，勿跳过校验强制覆盖。安装完成后刷新家庭网页。

## 2. 上传私人书籍

使用阿里云服务器文件管理，在 /home/admin/ 下新建 parenting-books 文件夹，把有权使用的书籍上传到这个文件夹。不需要发送到 GitHub，也不需要发送给聊天助手。

支持可提取文字的 PDF 和 UTF-8 TXT。不支持直接读取 EPUB、DOC、加密 PDF；扫描 PDF 需先 OCR。先用一本书验证，不要一次导入大量资料。

然后在服务器终端执行：

```bash
sudo install -d -m 700 -o parenting-agent -g parenting-agent /var/lib/parenting-agent/knowledge
sudo find /home/admin/parenting-books -maxdepth 1 -type f \( -iname '*.pdf' -o -iname '*.txt' \) -exec cp -n -- {} /var/lib/parenting-agent/knowledge/ \;
sudo chown -R parenting-agent:parenting-agent /var/lib/parenting-agent/knowledge
sudo find /var/lib/parenting-agent/knowledge -type f -exec chmod 600 {} \;
sudo -u parenting-agent env PARENTING_DATA_DIR=/var/lib/parenting-agent /opt/parenting-agent/.venv/bin/python /opt/parenting-agent/check_knowledge.py
```

同名书籍不会被这个复制命令覆盖。需要更新某本书时先保留原件，再在服务器文件管理中有意替换。检查输出只列文件名、状态和片段数，不打印书中正文、不调用外部接口。/home/admin/parenting-books 是上传中转文件夹，核对成功后可以自行移除其中的副本。

## 3. 核对收录与检索

1. 登录家庭网页，进入“育儿知识库”，展开“已收录资料与读取状态”。确认新书显示“已收录”。
2. 选择书中一条具体内容，在网页或飞书提问，检查来源是否有“私有/书名.pdf”和正确页码。
3. 如果只引用了原指南，说明该问题没有命中新书，不能据此断言读取失败；以收录状态和书中具体问题进一步核对。

命令行也可仅检查检索结果，不生成 AI 回答：

```bash
sudo -u parenting-agent env PARENTING_DATA_DIR=/var/lib/parenting-agent /opt/parenting-agent/.venv/bin/python /opt/parenting-agent/check_knowledge.py --question "如何开展亲子阅读"
```

新增、替换或移除资料后，下次检索会自动按文件变化重建进程内索引。只扫描目录第一层，不扫描子文件夹、不跟随链接。单文件上限 50MB，总计最多 8000 片段；超限整本暂不收录，状态会说明原因。索引只在内存保存，没有把原书或提取文本写入代码仓库。

原指南曾有一处经核对的文字提取修复；本次将修复范围限制为原指南，私人书籍不应用该文字补写。

## 4. 隐私范围

- 服务器书籍目录 /var/lib/parenting-agent/knowledge 在代码目录 /opt/parenting-agent 外。
- 默认本地 data/knowledge 已被 Git 忽略；自定义数据目录应放到仓库之外。
- 网页资料列表及引用位于家庭登录后的页面；书籍不添加到公开作品集或 GitHub。
- 模型回答时会收到问题和检索命中的片段。这不是完全离线的问答系统。
- 每日早教优先从已收录的私有书籍中摘取；没有合适内容或模型/原文核对失败时退回原指南。
- Git 忽略规则只影响未跟踪文件。若书籍以前已经提交，添加忽略规则不会移除 Git 历史；需另行核对处理。不要把私人书籍、正文摘录或真实家庭截图放入公开测试和评测报告。

## 5. 每日早教从新书摘取

本次版本为 2026.09.21-private-knowledge-tips-v6。与上一版私有知识库更新合并在同一个 update_private_knowledge.py 中；已装上一版也可执行新版，安装器会识别已知版本。

1. 书籍收录成功后，登录家庭网页“推送设置”，选择预览类型“早教知识”，点击“仅预览，不发送”。
2. 如果选到新书，应看到“今日书摘”、一小段原文和“私有/书名.pdf 第X页”。TXT 不虚构页码。
3. 原有早教开关、发送时间和家庭群继续有效；之前未开启的任务不会被安装器自动开启。

每天先从私有书籍收集最多12个早教候选片段，按日期轮换书籍和片段；使用现有 DeepSeek 接口选择一段40～180字的连续原文。程序验证来源、原文匹配及句子边界，返回原书中的实际文字，不能由模型自由编写一条“知识”。近30天已发送或送达不确定的相同摘录会避开；候选有限时可能使用备用指南。

新书不可读、没有合适片段、模型未选择或返回内容核对失败时，改用原先核对过的7条指南摘录并说明原因。备用指南本身也不可用时，该任务失败且不发送无来源内容。

筛选会调用现有 DeepSeek API；只发送候选片段，不发送整本书或宝宝档案。网页早教预览也可能调用一次筛选，但不会发送飞书消息或标记为已推送。命令行 verify_features.py 仍是离线只读检查，不会因新增书籍自动调用模型。

同一天已送达的定时任务不会因本次更新或重启再次发送。发送失败与送达不确定继续沿用原有状态核对流程。已发送信息不因书籍后来移除而从飞书或本地发送日志中消失。

原文匹配不等于验证书中观点的医学/教育有效性，也不代表自动判断适合宝宝当前发育水平。真实私有书籍的筛选质量需要先用网页预览核对。本次回归使用合成资料和模拟模型，没有发送真实飞书消息。

## 6. 同步本地源码和 GitHub

服务器更新和 GitHub 提交是两件事；只改服务器，GitHub 不会自动变化。也不要把整个服务器目录或数据备份上传 GitHub。

把同一个 update_private_knowledge.py 下载到电脑的 parenting-agent 项目文件夹。关闭本地运行的机器人、网页、定时服务，在项目 PowerShell 中执行：

```powershell
python .\update_private_knowledge.py --local
python -m pytest -q
git status --short
git check-ignore data/knowledge/example.pdf
git ls-files data/knowledge
```

仅在本地已有家庭功能时使用该同步方式；它会保留本地其他修改，遇到未知文件版本会停止。本次 README 和功能代码需要一起提交，不应单独发布一份与仓库代码不一致的 README。

git check-ignore 应显示 data/knowledge/example.pdf；git ls-files data/knowledge 应没有输出。如果后者列出文件，先核对这些已跟踪文件，不要立即推送。

下列是本项目家庭功能与知识库的源码清单，核对 git status 后按存在的路径暂存；不要使用包含数据目录的整目录打包：

```powershell
git add -- README.md .gitignore .env.example requirements.txt
git add -- agent_v2 family_features rag tests_v2 tests_features
git add -- feishu_bot.py streamlit_app.py photo_memory.py photo_memory_ui.py
git add -- configure_features.py verify_features.py run_scheduler.py cleanup_photo_cache.py check_knowledge.py
git add -- docs/FAMILY_FEATURES.md docs/FAMILY_VERIFICATION.md docs/RECORD_MANAGEMENT_FIX.md docs/DIARY_UI_UPDATE.md docs/PHOTO_CONVERSATION_UPDATE.md docs/PHOTO_MODAL_UPDATE.md docs/PRIVATE_KNOWLEDGE.md
git --no-pager diff --cached --stat
git --no-pager diff --cached --name-only
```

若 git status 还显示其他相关源码或部署脚本改动，请逐项核对补充，避免漏掉依赖。暂存清单不应出现 .env、宝宝数据、原始照片、私人书籍、服务器迁移包。确认清单后再提交和推送：

```powershell
git commit -m "同步家庭档案、照片交互与私有知识库功能及文档"
git push
git status -sb
```

本更新脚本本身不会执行 git add、commit 或 push，也不会连接 GitHub。
