# 视频工作流界面规范（中文）

## 设计目标
- 搭建一个三栏式控制台，帮助用户驱动多步骤智能体工作流。
- 视觉基调保持黑白极简，仅在需要强调状态时使用点缀色 `#6467F0`。
- 组件优先选用 [shadcn/ui](https://ui.shadcn.com) 提供的现成实现，除非确实不存在再自定义。

## 布局总览
```
| 用户输入 | 节点时间线 | 最终输出 |
```
- 页面外层使用 `Container` + `Grid` (`grid-cols-12 gap-6 px-8 py-6`)。
- 桌面端列宽建议 3 / 5 / 4；在 `md` 以下自动改为竖向堆叠。
- 若需要用户调整列宽，可替换为 `ResizablePanelGroup`（水平）。

## 左栏：用户输入
- 使用 `Card` 组织字段，`CardHeader` 放标题/描述，`CardContent` 放输入控件。
- 支持手动收起/展开：在卡片头部放置折叠图标，收起时仅保留窄侧栏与 Generate 图标/状态。
- 常用输入：
  - `Input`：视频标题或主题。
  - `Textarea`：长描述、脚本约束。
  - `Select`：模板或风格预设（可选）。
- `CardFooter` 放两个按钮：
  - **Generate**：`Button` 默认样式，触发后端开始工作流。
  - **Interrupt**：`Button variant="destructive"`；仅在运行中可点。
- 需要提示时，可在输入面板下方补一条 `Alert`，显示校验或最近系统消息。

## 中栏：节点时间线
- 外层 `Card` + `ScrollArea`，高度控制在 `calc(100vh - header)`。
- 背景使用低对比度的点阵纹理（如 `bg-dot-pattern` 或 `bg-[radial-gradient(...)]`），营造控制面板质感且不影响可读性。
- 无需进度条；改用节点状态体现节奏。
- 节点垂直排列，顺序固定为：`Scripter → Storyboard Images → Video Generation → Video Concatenation → BGM`。
- 每个节点可用子 `Card` 或自定义 `div`，内部包含：
  - 在工作流运行期间，整列节点设为只读，添加 `aria-disabled`，并通过 `pointer-events-none`、`cursor-not-allowed`（hover 时显示禁止符号）提示不可操作。
  - 单个节点限制 `max-h-[30vh]`（约等于视窗高度的 30%）与 `max-w-[80%]`，内部再用 `ScrollArea` 或 `overflow-y-auto` 处理溢出内容。
  - 卡片右上角放置“赞 / 踩”图标按钮，用户可即时对该节点产出表达态度；即使节点处于锁定状态也应可点。点击“踩”时弹出可关闭的小浮层，附带“你不喜欢的原因？”等可选提问输入，方便收集反馈再关闭。
  - 标题 + 状态 `Badge`（`variant="outline"` idle，`variant="secondary"` done）。
  - 运行时在卡片左侧加一条 `border-l-2 border-[#6467F0]`，或给整列套 `border-[#6467F0] shadow-[0_0_0_1px_#6467F0]`。
  - 内容区域：进行中的节点为实时流式输出（聊天形式），让用户看到最新日志；完成后可展示摘要、缩略图等。
- 整个中栏在 `isRunning` 时切换边框颜色 `border-[#6467F0]`；空闲时使用主题默认边框。
- Toast 反馈：通过 shadcn `useToast` 在中栏顶部的 `ToastViewport` 固定位置显示结果——工作流成功结束时弹出 success toast；若中途中断或失败，则弹出 destructive toast。

## 右栏：最终输出
- 仍然使用 `Card`，让内容按稳定顺序垂直排列：
  1. 标题（`CardHeader`）。
  2. 最终视频：`AspectRatio` 包装 `<video controls>`，展示 MP4。需要提供“放大”操作（悬浮按钮或覆盖层），点击后在 Modal / Lightbox 中展示全屏，关闭时自动回到卡片中原有尺寸。
  3. 脚本文字：`ScrollArea` + `pre-wrap`，必要时提供复制按钮。
  4. `Separator`。
  5. **Regenerate**：`Button variant="outline"`，重新触发最终渲染。
- 面板行为：
  - 第一次视频尚未生成时，右栏保持收起（在右侧仅显示窄卡片 + 空状态提示），并禁用内部操作。
  - 视频生成后自动展开，填充播放器与脚本；可视需要允许用户手动再次收起或展开。
- 空状态：用 `Skeleton` 占位；失败时以 `Alert variant="destructive"` 提示。

## 交互与状态
- **Idle**：Generate 可用，Interrupt 禁用；节点 `Badge` 显示 “Waiting”；中栏为默认边框。
- **Running**：Generate 禁用，Interrupt 可用；当前节点添加 `animate-pulse` 或 loading 图标；中栏高亮 `#6467F0`。
- **Interrupted / Error**：在中栏顶部显示 `Alert`，未完成节点保持“Waiting”，已完成节点保持“Done”。
- **Regenerate**：只刷新右栏输出，可考虑在下方用 `Accordion` 保留历史版本（可选）。

## 响应式与无障碍
- `md` 以下三列改为纵向 `flex`，按钮占满行。
- 所有按钮与节点状态添加 `aria-live` / `aria-busy` 信息。
- 注意在深色模式下仍然保持黑白主色 + `#6467F0` 点缀的对比度。

## 数据与状态管理
- 建议用 React Context 或 `zustand` 存储节点状态、输出路径和运行标志，三列组件同时订阅。
- 节点列表由一个数组驱动，便于按需新增步骤。
- Regenerate 按钮调用专属 API，仅刷新最终视频与脚本，不影响左侧输入。

## 其他说明
- 无法提前估算耗时，因此不展示进度条。
- 排版遵循 shadcn 默认字体（`font-sans`）和字号层级，保持整洁可读。

