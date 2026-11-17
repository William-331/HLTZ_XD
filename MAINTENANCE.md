# 扣子的猫窝

这份项目发布到 `William-331/William-331` 后，根目录 README 会出现在 GitHub 个人主页。`site/` 是独立互动猫窝，通过项目级 GitHub Pages 发布到 `https://william-331.github.io/William-331/`，不会覆盖原来的 `William-331.github.io` 项目。

## 已实现

- 小猫叫扣子。原画像素猫与房间，深浅两种配色，README 中可显示 SVG 眨眼动画。
- 自动查询所有公开自有仓库，排除 fork、归档、禁用、空仓库与个人主页仓库。优先 `kouzi-featured` Topic，其次按最后推送时间，最多展示 4 个。
- 仓库简介为空时自动用语言生成通用介绍；无需为新增仓库写专属卡片。项目名、介绍与链接直接来自 GitHub。所有文本会转义。
- 领养日为 2026-11-17。按 GitHub 返回的贡献日历 UTC 日期计算：0 次=0 XP，1–3 次=5 XP，4–9 次=8 XP，10 次以上=10 XP。每级 60 XP。
- 按日期保存独立成长账本。重复运行不重复加分；同一天贡献升级档位时只补差额；休息与后续贡献修订不扣已获得经验。
- 每次回看最近 35 天（及首次/中断后尚未同步的日期）来补记贡献。API 失败、日期不完整或数据异常时退出，保留现有账本与页面；不会把失败当成零。
- 贡献摘要遵循 GitHub 本身的日历口径；只获取聚合贡献数，不导出私人仓库信息。若个人主页开启私人贡献计数，聚合总数可能包括这些匿名计数。
- 七天猫爪足迹、等级阶段、已解锁装饰自动更新。Lv.2 猫窝/毛线球/绿植，Lv.4 窗边坐垫，Lv.6 纪念画。
- 猫窝支持喂食、玩耍、休息、深浅主题、README 带动作链接。互动状态本机保存 24 小时，不改变真实经验，不产生虚构提交，也不收集访客信息。

## 自动化

`Update Kouzi profile` 每天 **12:17 UTC** 运行，可随时从 Actions 手动运行。GitHub 定时任务可能延迟，贡献也可能延迟计入。生成结果有变化才提交；作者是 GitHub Actions 机器人，不会给 William 刷贡献。

`Deploy Kouzi home` 在站点文件变化、数据更新工作流成功或手动触发时部署 `site/`。之所以监听 `workflow_run`，是因为默认 GITHUB_TOKEN 的提交不会再次触发普通 push 工作流。

工作流只使用 GitHub 自带的 `github.token`。更新任务有仓库内容写入权限；部署任务只有所需的 Pages/身份令牌权限。不需要额外的个人 PAT。

## 调整方式

编辑 `profile.config.json` 可以调整猫名、展示数量、排除仓库与目标链接。已经领养后不要改 `adopted_on`，生成器会拒绝意外重置。给仓库添加 `kouzi-featured` Topic 可以让它常驻优先，无需编辑 README；移除 Topic 后恢复按更新时间选择。更新延迟最多到下一次定时同步，也可手动运行 Actions。

项目卡片基于仓库级别 `pushed_at` 排序；任何分支的推送都可能影响顺序。更新只筛选公开仓库，卡片永远不会暴露私人项目。

## 本地运行与检查

Python 3.11+，只用标准库，无 pip 依赖：

```sh
python -m unittest discover -s tests -v
python scripts/update_profile.py --use-git-credential
python -m http.server 8765 --directory site
```

本机生成器可读取现有 Git 凭据（显式加 `--use-git-credential`）；也可从 `GH_TOKEN` 或 `GITHUB_TOKEN` 环境变量读取。不会打印或保存令牌。仅含默认读取权限的令牌可能需要确保可查询公开用户贡献 GraphQL 接口；若 Actions 报权限错误，应先查看实际错误再调整，不要直接使用全权限令牌。

`site/index.html` 也能直接用浏览器打开（数据通过本地 `data.js` 加载，无需 API 请求）。本机浏览器禁止存储时仍可互动，只是不记住选择。

## 文件

- `scripts/update_profile.py`：拉取数据、成长结算、生成 README 和站点数据。
- `scripts/pet_art.py`：像素猫窝、项目卡片、猫爪日历的 SVG 绘制。
- `data/growth.json`：成长账本，应随代码保留，不要手动清空。
- `data/profile.json`：当前公开状态快照。
- `site/`：可独立托管的互动猫窝，无第三方脚本或字体。
- `.github/workflows/`：每日更新与 Pages 部署。
- `tests/`：阈值、幂等、补记、数据筛选、转义及失败保留的回归检查。

不要修改生成后的 README 或卡片来添加新项目；下一次同步会覆盖它们。版式修改请编辑生成脚本。旧版个人主页草稿已单独备份，不随本项目公开。
