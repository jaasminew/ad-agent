export const translations = {
  en: {
    header: {
      eyebrow: "Agent Control Room",
      title: "Commercial Video Generation Agent",
      description:
        "An autonomous agent that turns scripts into cinematic commercial videos through smart planning, reference search, and iterative visual refinement.",
      badge: "Preliminary Version",
    },
    statusMessages: {
      running: "Agent is running the current workflow.",
      interrupted: "Last run was interrupted. You can resume when ready.",
      idle: "Standing by. Provide a prompt and hit generate.",
    },
    themeToggle: {
      toLight: "Switch to light mode",
      toDark: "Switch to dark mode",
    },
    languageToggle: {
      toChinese: "Switch to Chinese",
      toEnglish: "Switch to English",
    },
    inputPanel: {
      title: "User Input",
      description: "Provide the prompt and context for the agent workflow.",
      fields: {
        productName: {
          label: "Product Name",
          placeholder: "Product teaser for NOVA earbuds",
        },
        brandIdentity: {
          label: "Brand Identity",
          placeholder:
            "Highlight hybrid noise-canceling, adaptive EQ, and 36h battery. Set mood: futuristic studio with neon rim light.",
        },
        productImage: {
          label: "Product Image",
        },
        mustHaveShots: {
          label: "Must Have Shots",
        },
        numberOfShots: {
          label: "Number of Shots",
          placeholder: "6",
        },
        videoFormat: {
          label: "Video Format",
        },
      },
      dropzone: {
        helperText: "Upload packaging renders, hero shots, or brand references.",
        selectedPrefix: "Selected:",
      },
      shotHelperSuggestions: [
        "Problem hook in transit",
        "Close-up of earbuds + UI overlay",
        "Lifestyle hero in neon studio",
      ],
      videoFormatOptions: ["16:9 Landscape", "9:16 Vertical", "1:1 Square"],
      actions: {
        generate: "Generate",
        generating: "Generating…",
        interrupt: "Interrupt",
      },
    },
    validation: {
      missingProductName: {
        title: "Missing product name",
        description: "Add a product name before generating.",
      },
      missingBrandIdentity: {
        title: "Missing brand identity",
        description: "Share a few lines about the brand to guide the agent.",
      },
      missingProductImage: {
        title: "Missing product image",
        description: "Upload a hero image so the agent can stay on brand.",
      },
      invalidShotCount: {
        title: "Invalid shot count",
        description: "Set the number of shots to a positive integer.",
      },
      missingVideoFormat: {
        title: "Select a video format",
        description: "Pick one or more aspect ratios for the final delivery.",
      },
    },
    toasts: {
      workflowInterrupted: {
        title: "Workflow interrupted",
        description: "The agent stopped mid-run. Resume when ready.",
      },
      workflowFinished: {
        title: "Workflow finished",
        description: "All nodes executed successfully.",
      },
      interruptSent: {
        title: "Interrupt sent",
        description: "We’ll keep the current outputs for reference.",
      },
      finalRenderRefreshed: {
        title: "Final render refreshed",
        description: "A new cut is ready in the output panel.",
      },
    },
    interruptDialog: {
      title: "Interrupt this run?",
      description:
        "Stopping now cancels the remaining nodes. Partial outputs stay in the timeline so you can adjust the brief and restart.",
      cancel: "Keep running",
      confirm: "Stop workflow",
      confirming: "Stopping…",
      errorTitle: "Failed to interrupt",
      errorDescription: "Please try again in a moment.",
    },
    workflow: {
      processingFallback: "Processing...",
      streamingScripts: {
        script_gen_agent: [
          "Scanning the brief...",
          "Drafting a cold-open hook with a tangible problem.",
          "Outlining 6 shots to cover setup, payoff, CTA.",
          "Polishing dialogue beats to feel human.",
        ],
        storyboard_gen_agent: [
          "Generating reference boards for each planned shot.",
          "Locking framing cues and camera moves.",
          "Highlighting motion guidance for the video model.",
        ],
        video_generator: [
          "Sending prompts to the video model.",
          "Receiving first cut assets...",
          "Reinforcing color palette per brand guide.",
        ],
        video_concatenater: [
          "Aligning clip lengths to the script pacing.",
          "Dropping in placeholders for transitions.",
          "Normalizing loudness across clips.",
        ],
        bgm_generator: [
          "Sketching melody inspired by synthwave references.",
          "Balancing drums to leave space for narration.",
          "Exporting final mix at -14 LUFS.",
        ],
      },
    },
    timeline: {
      title: "Node Timeline",
      description: "Nodes lock while the workflow is running.",
      statusBadge: {
        running: "Running",
        interrupted: "Interrupted",
        idle: "Idle",
      },
      alertTitle: "Workflow stopped",
      alertDescription:
        "Resume the run or update your prompt before re-launching.",
      emptyState: "Nodes appear after you start a run or once outputs are ready.",
    },
    nodeCard: {
      statusBadges: {
        waiting: "Waiting",
        running: "Running",
        done: "Done",
        error: "Error",
      },
      waitingMessage: "Waiting for output…",
      feedbackPrompt: "What missed the mark?",
      feedbackPlaceholder: "Add optional context",
      feedbackSubmit: "Submit feedback",
      thumbsUpAria: "Thumbs up",
      thumbsDownAria: "Thumbs down",
    },
    finalOutput: {
      title: "Final Output",
      description: "Video preview and script transcript.",
      statusLabel: "Status",
      emptyMessage: "Generate at least once to bring this panel to life.",
      readyBadge: "Ready",
      scriptLabel: "Script Transcript",
      historyTitle: "Previous renders",
      regenerate: "Regenerate",
      regenerating: "Regenerating…",
      videoButton: {
        expand: "Expand video",
        collapse: "Collapse video",
      },
    },
    stackedFallback: {
      desktopTitle: "Desktop experience",
      desktopDescription:
        "Resize to a larger viewport to access the resizable control room. This mobile view keeps key actions reachable.",
      userInputTitle: "User Input",
      nodeTimelineTitle: "Node Timeline",
      finalOutputTitle: "Final Output",
      nodesAppear:
        "Nodes appear after you start a run or once outputs are available.",
    },
    lightbox: {
      close: "Close",
    },
    nodes: {
      script_gen_agent: {
        label: "Scripter",
        waitingSummary: "Waiting for the story script.",
        doneSummary: "Story outline locked with a 45-second runtime.",
      },
      storyboard_gen_agent: {
        label: "Storyboard Images",
        waitingSummary: "Waiting for storyboard drafts.",
        doneSummary: "Storyboard includes 6 hero frames and transition cues.",
      },
      video_generator: {
        label: "Video Generation",
        waitingSummary: "Waiting to render the footage.",
        doneSummary: "Core footage rendered in UHD, matching the palette.",
      },
      video_concatenater: {
        label: "Video Concatenation",
        waitingSummary: "Waiting to stitch clips together.",
        doneSummary: "All segments stitched with crossfades + bumper outro.",
      },
      bgm_generator: {
        label: "BGM",
        waitingSummary: "Waiting to compose background music.",
        doneSummary: "Custom BGM track mastered and synced to beat markers.",
      },
    },
  },
  zh: {
    header: {
      eyebrow: "智能体控制室",
      title: "视频工作流指挥中心",
      description:
        "一款借助智能规划、参考检索与迭代视觉润色，将脚本化为电影级商业广告的视频智能体。",
      badge: "Preliminary Version",
    },
    statusMessages: {
      running: "智能体正在执行当前工作流。",
      interrupted: "上次运行已被中断，可以随时恢复。",
      idle: "待命中。填写提示后点击生成。",
    },
    themeToggle: {
      toLight: "切换为亮色模式",
      toDark: "切换为暗色模式",
    },
    languageToggle: {
      toChinese: "切换为中文",
      toEnglish: "切换为英文",
    },
    inputPanel: {
      title: "用户输入",
      description: "为智能体工作流提供提示与上下文。",
      fields: {
        productName: {
          label: "产品名称",
          placeholder: "NOVA 耳机产品预告",
        },
        brandIdentity: {
          label: "品牌调性",
          placeholder: "突出混合降噪、自适应 EQ、36 小时续航。氛围：霓虹边缘灯未来感棚拍。",
        },
        productImage: {
          label: "产品图片",
        },
        mustHaveShots: {
          label: "必须出现的镜头",
        },
        numberOfShots: {
          label: "镜头数量",
          placeholder: "6",
        },
        videoFormat: {
          label: "视频比例",
        },
      },
      dropzone: {
        helperText: "上传包装渲染、主视觉或品牌参考。",
        selectedPrefix: "已选择：",
      },
      shotHelperSuggestions: [
        "通勤场景提出痛点",
        "耳机特写 + UI 叠加",
        "霓虹棚里的生活方式主角",
      ],
      videoFormatOptions: ["16:9 横屏", "9:16 竖屏", "1:1 方形"],
      actions: {
        generate: "生成",
        generating: "生成中…",
        interrupt: "中断",
      },
    },
    validation: {
      missingProductName: {
        title: "缺少产品名称",
        description: "生成前请先填写产品名称。",
      },
      missingBrandIdentity: {
        title: "缺少品牌调性",
        description: "写几句品牌背景，方便智能体对齐。",
      },
      missingProductImage: {
        title: "缺少产品图片",
        description: "请上传至少一张产品图，方便智能体对齐品牌。",
      },
      invalidShotCount: {
        title: "镜头数量无效",
        description: "请填写一个大于 0 的整数。",
      },
      missingVideoFormat: {
        title: "请选择视频比例",
        description: "至少勾选一种交付比例。",
      },
    },
    toasts: {
      workflowInterrupted: {
        title: "工作流已中断",
        description: "智能体在运行中被停止，准备好后再继续。",
      },
      workflowFinished: {
        title: "工作流完成",
        description: "所有节点均已成功执行。",
      },
      interruptSent: {
        title: "已发送中断",
        description: "我们会保留当前输出供参考。",
      },
      finalRenderRefreshed: {
        title: "终版渲染已刷新",
        description: "输出面板里已经更新了新的版本。",
      },
    },
    interruptDialog: {
      title: "确定要中断当前流程？",
      description:
        "现在停止会立即取消剩余节点，已有输出仍会保留，方便你稍后调整并重新运行。",
      cancel: "继续运行",
      confirm: "立即停止",
      confirming: "正在停止…",
      errorTitle: "中断失败",
      errorDescription: "稍后再试一次。",
    },
    workflow: {
      processingFallback: "处理中…",
      streamingScripts: {
        script_gen_agent: [
          "解析简报…",
          "撰写以真实痛点开场的钩子。",
          "规划 6 个镜头覆盖铺垫、转折、CTA。",
          "润色对白节奏让其更自然。",
        ],
        storyboard_gen_agent: [
          "为每个镜头生成参考分镜。",
          "锁定构图提示与镜头运动。",
          "标注供视频模型参考的运动引导。",
        ],
        video_generator: [
          "向视频模型发送提示。",
          "接收第一版素材…",
          "根据品牌色强化调色。",
        ],
        video_concatenater: [
          "校准片段长度以匹配脚本节奏。",
          "为转场添加占位。",
          "统一所有片段的响度。",
        ],
        bgm_generator: [
          "根据合成波参考勾勒旋律。",
          "平衡鼓点，为旁白留出空间。",
          "以 -14 LUFS 导出终版混音。",
        ],
      },
    },
    timeline: {
      title: "节点时间线",
      description: "工作流运行时节点会被锁定。",
      statusBadge: {
        running: "运行中",
        interrupted: "已中断",
        idle: "空闲",
      },
      alertTitle: "工作流已停止",
      alertDescription: "可继续运行或更新提示后再启动。",
      emptyState: "启动运行或生成输出后即可查看节点。",
    },
    nodeCard: {
      statusBadges: {
        waiting: "等待",
        running: "运行中",
        done: "完成",
        error: "出错",
      },
      waitingMessage: "等待输出…",
      feedbackPrompt: "哪里不够理想？",
      feedbackPlaceholder: "可选说明",
      feedbackSubmit: "提交反馈",
      thumbsUpAria: "点赞",
      thumbsDownAria: "点踩",
    },
    finalOutput: {
      title: "最终输出",
      description: "视频预览与脚本文字。",
      statusLabel: "状态",
      emptyMessage: "至少生成一次即可激活此面板。",
      readyBadge: "就绪",
      scriptLabel: "脚本文本",
      historyTitle: "历史渲染",
      regenerate: "重新生成",
      regenerating: "重新生成中…",
      videoButton: {
        expand: "放大视频",
        collapse: "收起视频",
      },
    },
    stackedFallback: {
      desktopTitle: "桌面体验",
      desktopDescription:
        "放大浏览器窗口即可启用可调整的控制室。移动视图保留关键操作。",
      userInputTitle: "用户输入",
      nodeTimelineTitle: "节点时间线",
      finalOutputTitle: "最终输出",
      nodesAppear: "启动运行或完成输出后即可看到节点。",
    },
    lightbox: {
      close: "关闭",
    },
    nodes: {
      script_gen_agent: {
        label: "脚本生成",
        waitingSummary: "等待脚本输出。",
        doneSummary: "45 秒脚本结构已锁定。",
      },
      storyboard_gen_agent: {
        label: "分镜图",
        waitingSummary: "等待分镜草图。",
        doneSummary: "分镜包含 6 个关键画面和转场提示。",
      },
      video_generator: {
        label: "视频生成",
        waitingSummary: "等待渲染画面。",
        doneSummary: "核心画面以 UHD 输出，并匹配品牌配色。",
      },
      video_concatenater: {
        label: "视频拼接",
        waitingSummary: "等待拼接片段。",
        doneSummary: "所有段落已衔接并添加首尾转场。",
      },
      bgm_generator: {
        label: "背景音乐",
        waitingSummary: "等待编曲。",
        doneSummary: "定制 BGM 已混音并对齐节拍标记。",
      },
    },
  },
} as const

export type Language = keyof typeof translations
export type AppCopy = (typeof translations)[Language]

