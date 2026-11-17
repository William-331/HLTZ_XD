# 扣子的 GitHub 主页

主要入口为 https://github.com/William-331 。同名仓库的 README 直接渲染在 GitHub 个人主页。所有功能均在 README 中展示；折叠区使用 GitHub 支持的 `<details>`，自绘 SVG 随 GitHub 深浅主题切换。

## 页面内容

- 像素猫窝：贡献状态决定扣子在休息、陪写代码还是玩毛线。眨眼支持减少动态效果偏好。
- 成长手账：等级、经验条、距离升级所需经验、一起生活天数和收藏章数量。
- 今日便签：按 UTC 日期轮换，每次刷新保持一致。
- 七日猫爪足迹，以及可展开的全年猫爪花园；日期窗口使用 GitHub 接口实际返回值。
- 收藏册：入住、首次经验、领养后 3/7 个活跃日、3 个公开原创项目、Lv.2。活跃日来自成长账本，不追溯领养前历史。fork 和归档项目不计入项目收藏章。
- 翻纸箱：嵌套折叠区可直接展开，每天三个纸箱里有一个小宝藏。不记录点击，不发放经验。
- 自动项目卡片、全部公开仓库表、技术零食柜：每天同步；缺少简介时按语言生成通用介绍。
- 巡逻日志：公开提交、创建仓库、Issue、PR 等贡献，默认 5 条，展开最多 20 条。不是完整 GitHub 事件审计。

不再提供网页版喂食、玩耍、搜索等脚本功能，不再发布项目级猫窝网站。旧网页已在本次任务工作文件夹备份。原有 William-331.github.io 仓库和站点不受此项目影响。

## 成长规则

领养日固定为 2026-11-17。按 GitHub 贡献日历日期结算：0 次=0 XP，1–3 次=5 XP，4–9 次=8 XP，10 次及以上=10 XP。每 60 XP 升一级，休息不扣分。每日独立账本可重复执行；同一天仅补档位差额。贡献被后续修订也保留已获得经验。

Lv.2 解锁地毯、毛线球与绿植；Lv.4 窗边坐垫；Lv.6 纪念画。图像随每日同步重新生成。

## 自动更新

Update Kouzi profile 每日 12:17 UTC 执行，支持 Actions 手动运行及配置、脚本、测试变更触发。GitHub 定时任务和贡献统计可能延迟。机器人提交不计作 William 的贡献。

同步前运行 Python 回归测试。所有必需 API 校验成功才写文件；失败保留上次页面。公开数据可能与登录后不同，不公布私人仓库名和不可见组织关系。不再复制其他仓库的完整 README，只收录公开元数据。

profile.config.json 可配置项目数量（1–12）及优先 Topic kouzi-featured。卡片排除个人主页仓库、fork、归档、禁用和空仓库；全部公开仓库表列出所有公开自有仓库。

## 本地维护

```powershell
python -m unittest discover -s tests -v
python scripts/update_profile.py --use-git-credential
```

需要 Python 3.11+，无第三方包。Actions 使用内置 github.token。本地复用已有 Git 凭据，不保存或打印令牌。不要修改领养日或删除 data/growth.json。

README.md、assets/、data/ 为生成文件。持久修改应写入 scripts/update_profile.py 和 scripts/pet_art.py。
