# 市政门牌别名归并与改址公示

长桥街道地址办有4位采集员、2位核定员，过去用地籍图、门牌照片和Excel分别登记，历史“十八号”与现“18号”重复建档；同街81号又容易被误合；居民意见与公示期限靠口头交接。本项目把实地入口、旧名书证、归并核验、公示和目录映射贯通。上游为现场采集与住户意见，下游为街道服务窗口查询到的正式入口。全部数据模拟，不接入外部政务目录。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build --wait
```

前端 http://localhost:18235，API http://localhost:19235/docs，MySQL localhost:17735。Compose 恰好 frontend/backend/worker/db/redis 五服务，各有健康检查，MySQL8采用READ COMMITTED。演示账号 `operator@changqiao.local`、`supervisor@changqiao.local`、`viewer@changqiao.local`，口令 `Address2026!`。

| 角色 | 页面与权限 | 典型动作 |
|---|---|---|
| operator | 六页可读，入口/别名/证据/候选/提案/异议可写 | 现场采集旧门牌与提出归并 |
| supervisor | 全部日常动作及复核、公示、生效、回滚、演示时钟 | 签核异议和更新服务目录 |
| viewer | 六页只读，后端所有写接口拒绝 | 查看公示期限及旧址路径 |

`.env.example` 包含 COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、DOCKER_SUBNET、JWT_SECRET，生产部署应更换演示凭据。卷保存MySQL、Redis和worker心跳。中文和空格路径已实测。

## 六个模块与状态

1. 实地门牌：Entrance记录唯一采集号、街道、门牌数字与经纬度，坐标更正留审计；不因文字近似删除独立入口。
2. 别名书证：Alias归属入口，Evidence有唯一文件/照片参考号和现场核验说明；来源无证据禁止公示。
3. 候选归并：真实worker字符TF-IDF与层次聚类给出候选、相似度和数字冲突；Proposal独立记录来源目标和人工理由。同街同号才可形成提案。
4. 住户异议：Objection open→resolved，核定维持归并或split拆分；拆分把提案置rejected、公示withdrawn，仍保留两个入口。
5. 改址公示：Proposal draft→public→active，Notice至少3天；期限未满、异议未结、来源已有有效映射、映射成环均拒绝生效。
6. 服务目录：Redirect保存source→target及原提案，逐跳解析canonical。回滚置rolled_back并保留原因、公示和原目标；不是删除历史。所有图写操作先锁Registry父资源，防止并发生效绕过单来源约束或无环检查。

## 一天的剧本

1. 2026-11-18 09:00采集员核对CQ-018-A正门坐标与CQ-018-B旧“十八号”照片。
2. 在别名页核对照片-CQ-018-B，补录旧称和地籍图说明。
3. 运行别名匹配，比较十八号/18号，81号显示数字冲突，后端同样禁止归并。
4. 查看P031归并提案，登记Y031住户关于南入口的异议。
5. 核定员发布3天公示；当日生效按钮返回“公示期限未满”。
6. 使用明确的演示时钟推进到11月21日09:00；未处理Y031仍无法生效。
7. 核定员现场核验后维持归并，公示生效，CQ-018-B解析到CQ-018-A。
8. 发现入口独立则回滚映射，旧入口恢复自身canonical，原映射及原因仍可查；异议split可在生效前直接撤提案。

演示时钟保存在Registry，仅核定员可单向推进并留审计，不会依赖机器日期令种子失效。

## Python计算与可重复性

`matching.py`先将中文十八号规范为18号，char TF-IDF 1–3gram，余弦相似度与AgglomerativeClustering平均连接（预计算距离，阈值0.55）建立别名簇；跨入口最大余弦给出候选，门牌数字/道路不符只列冲突。归并动作不自动执行，必须人工建提案并公示。

48个模拟历史标注对按seed42分36训练/12留出；向量器只拟合训练文本，阈值从0.35–0.75仅按训练精确率+召回率选择；最终留出精确率1、召回率1。真实登记语料另行拟合无监督候选，不能把模拟标注得分当真实地址准确率。结果保存训练/留出ID、阈值、源数据SHA256与簇标签。文本不足真实failed，可补别名重新提交新匹配。

## 代码与开发

Python FastAPI / SQLAlchemy / MySQL8 / Redis7 / scikit-learn；原生HTML/CSS/JS ES modules + Nginx。backend/src/models.py为独立关系模型，schemas.py严格类型与长度范围；entrance_service、proposal_service、publication_service、directory_service分别承担现场、异议、期限、无环图规则。routes.py做JWT角色入口；worker.py运行真实计算；common.py管Registry锁与审计。middlewares.py含RequestTrace/Recovery两中间件。

frontend/src/pages下六页与业务模块对应；components/registry.js共享门牌牌面、状态徽标、标题和表单；utils/api.js管理会话与聚合store，utils/format.js管转义与数据类型。角色和状态枚举分别在backend/src/constants.py、frontend/src/constants.js（模型中持久化值同义）。

```bash
docker compose exec -T backend python scripts/seed_demo.py
docker compose exec -T backend python scripts/seed_demo.py
docker compose logs worker
docker compose down -v --remove-orphans
```

seed自然键仅补缺，已有坐标、提案、公示、映射和用户编辑不覆盖。测试脚本/日志/截图在交付根test-artifacts/gb-1036，源码不夹产物。后端可在本地Python3.12虚拟环境安装requirements后配置DATABASE_URL/REDIS_URL运行uvicorn；前端经nginx代理/api，无打包步骤。

## 已知边界

单街道模拟，不验证真实地籍权属；门牌中文数字规范仅支持1–99常见写法，不是全国地址标准化引擎。证据是文本文件参考号，不上传照片文件；未提供居民实名认证和外部目录推送。全图Registry锁优先小规模正确性，吞吐有限。BLPOP是轻量队列，进程在弹出后被杀不会自动重投；可新建匹配任务。时间按演示本地无时区ISO工作时钟处理；create_all不含生产迁移。

License: MIT（本项目新增代码）。
