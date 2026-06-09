import React, { ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Download,
  FileText,
  FolderTree,
  Gauge,
  LayoutDashboard,
  ListChecks,
  Loader2,
  Moon,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  ScrollText,
  Search,
  Settings,
  Square,
  Sun,
  Terminal,
  Trash2,
  X,
  XCircle
} from "lucide-react";
import "./styles.css";

const API = "/api/v1";

type Page = "projects" | "workbench" | "assets" | "chapters" | "export" | "logs" | "settings";

type ProjectSummary = {
  project_name: string;
  novel_name: string | null;
  genre: string;
  language: "zh" | "en";
  provider: "claude" | "codex";
  status: string;
  run_source?: "api" | "cli" | string | null;
  run_pid?: number | null;
  run_started_at?: string | null;
  run_id?: string | null;
  stage: string;
  progress_percent: number;
  chapter_progress: { generated: number; target: number | null };
  last_step: string | null;
  last_step_name: string | null;
  last_active_at: string;
  has_checkpoint: boolean;
  has_errors: boolean;
  can_continue: boolean;
  is_complete: boolean;
};

type FileNode = {
  name: string;
  relative_path: string;
  kind: string;
  is_directory: boolean;
  size: number;
  updated_at: string;
  health: string;
  children: FileNode[] | null;
};

type Chapter = {
  index: number;
  title: string;
  relative_path: string;
  word_count: number;
  updated_at: string;
  health: string;
};

type LogEntry = {
  log_id: string;
  updated_at: string;
  size: number;
  step: string | null;
  source: string;
};

type GenrePreset = {
  id: string;
  channel_id: string;
  genre_id: string;
  channel_name: string;
  genre_name: string;
  theme_name: string;
  description: string;
};

type RunRecord = {
  run_id: string;
  project_name: string;
  mode: string;
  status: string;
  command: string[];
  log_path: string | null;
  pid?: number | null;
  source?: string | null;
};

type RunLogState = {
  run: RunRecord | null;
  lines: string[];
  updatedAt: string | null;
  replaySkip?: string[];
};

type ParsedLogEvent = {
  type: "command" | "section" | "step" | "success" | "warning" | "error" | "rename" | "note";
  title: string;
  detail?: string;
  sourceIndex: number;
};

type CreativeOption = {
  index: number;
  title: string;
  opening: string;
  ref_works: string;
  content: string;
  relative_path: string;
  exists: boolean;
  selected: boolean;
};

type FileContent = {
  project_name: string;
  relative_path: string;
  kind: string;
  encoding: string;
  content: string;
  size: number;
  updated_at: string;
  sha256: string;
  editable: boolean;
};

class AppErrorBoundary extends React.Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="app-error-screen">
        <div>
          <h1>前端渲染异常</h1>
          <p>{this.state.error.message}</p>
          <div className="action-row">
            <button className="primary-button" onClick={() => window.location.reload()}>重新加载</button>
            <button className="secondary-button" onClick={() => { localStorage.removeItem("woke_novel_page"); window.location.reload(); }}>回到项目总览</button>
          </div>
        </div>
      </div>
    );
  }
}

const NOVEL_SIZE_OPTIONS = [
  { value: "短篇", label: "短篇", words: "约 8 万字" },
  { value: "中篇", label: "中篇", words: "约 30 万字" },
  { value: "长篇", label: "长篇", words: "约 80 万字" },
  { value: "超长篇", label: "超长篇", words: "约 150 万字" }
];

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const text = new TextDecoder("utf-8").decode(await res.arrayBuffer());
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const message = data?.error?.message || data?.detail || res.statusText;
    throw new Error(message);
  }
  return data as T;
}

function formatTime(value?: string | null) {
  if (!value) return "未记录";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function hasMetChapterTarget(project: ProjectSummary) {
  const target = project.chapter_progress.target;
  return typeof target === "number" && target > 0 && project.chapter_progress.generated >= target;
}

function isProjectComplete(project: ProjectSummary) {
  return project.is_complete || hasMetChapterTarget(project);
}

function canProjectContinue(project: ProjectSummary) {
  return project.can_continue && !isProjectComplete(project);
}

function statusLabel(project: ProjectSummary) {
  if (project.status === "running") return project.run_source === "cli" ? "CLI 运行中" : "运行中";
  if (isProjectComplete(project)) return "完成";
  if (canProjectContinue(project)) return "可续写";
  return "待启动";
}

function statusClass(project: ProjectSummary) {
  if (project.status === "running") return "badge running";
  if (isProjectComplete(project)) return "badge success";
  return "badge";
}

function runStatusLabel(status?: string | null) {
  if (status === "running") return "运行中";
  if (status === "queued") return "排队中";
  if (status === "failed") return "失败";
  if (status === "succeeded") return "已完成";
  if (status === "cancelled") return "已取消";
  return "空闲";
}

function workflowStatusLabel(status?: string | null) {
  if (status === "running") return "进行中";
  if (status === "succeeded") return "已完成";
  if (status === "failed") return "失败";
  return "未开始";
}

type TimelineStepStatus = "not_started" | "running" | "succeeded" | "failed";

type TimelineStep = {
  code: string;
  name: string;
  status: TimelineStepStatus;
};

const LINEAR_WORKFLOW_SECTIONS = [
  {
    key: "creative",
    name: "创意",
    note: "候选方案与方案补充",
    steps: [
      ["01", "创意方案"],
      ["02", "方案补充"]
    ]
  },
  {
    key: "world",
    name: "世界/人物",
    note: "设定、人设与关系矩阵",
    steps: [
      ["03", "世界观"],
      ["04", "人物关系"]
    ]
  },
  {
    key: "axis",
    name: "主轴",
    note: "故事主轴、幕次与项目记忆",
    steps: [
      ["05", "故事主轴"],
      ["05a", "幕次框架"],
      ["05b", "幕次骨架"],
      ["18", "项目记忆"]
    ]
  },
  {
    key: "opening",
    name: "开篇",
    note: "首章剧情、指南、正文与状态",
    steps: [
      ["06", "剧情提取"],
      ["07", "开篇梗概"],
      ["08", "写作指南"],
      ["09", "首章正文"],
      ["10", "状态文档"]
    ]
  }
] as const;

const LOOP_WORKFLOW_STEPS = [
  ["11", "方向指导"],
  ["12", "剧情梗概"],
  ["13", "写作指南"],
  ["14", "正文创作"],
  ["15", "状态文档"],
  ["16", "梗概精简"]
] as const;

const ACT_END_WORKFLOW_STEPS = [
  ["17", "幕次精简"],
  ["18", "项目记忆"]
] as const;

function projectRelativePath(project: string, path: string) {
  const normalized = path.replace(/\\/g, "/");
  const prefix = `projects/${project}/`;
  return normalized.startsWith(prefix) ? normalized.slice(prefix.length) : normalized;
}

function cleanLogLine(line: string) {
  return line
    .replace(/\x1B\[[0-?]*[ -/]*[@-~]/g, "")
    .replace(/[✓✗⚠▶✎★✦─═]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function parseLogEvents(lines: string[]): ParsedLogEvent[] {
  const events: ParsedLogEvent[] = [];
  lines.forEach((line, index) => {
    const text = cleanLogLine(line);
    if (!text) return;
    const structured = text.match(/^\[[^\]]+\]\s+(COMMAND|STEP|SECTION|OK|WARN|ERROR|RENAME|NOTE)\s+(.+)$/);
    if (structured) {
      const kind = structured[1];
      const body = structured[2];
      const typeMap: Record<string, ParsedLogEvent["type"]> = {
        COMMAND: "command",
        STEP: "step",
        SECTION: "section",
        OK: "success",
        WARN: "warning",
        ERROR: "error",
        RENAME: "rename",
        NOTE: "note"
      };
      events.push({ type: typeMap[kind] || "note", title: body, sourceIndex: index });
      return;
    }
    const commandLine = text.match(/^\[[^\]]+\]\s+command:\s+(.+)$/);
    if (commandLine) {
      events.push({ type: "command", title: "启动命令", detail: commandLine[1], sourceIndex: index });
      return;
    }
    if (text.startsWith("$ ")) {
      events.push({ type: "command", title: "启动命令", detail: text.slice(2), sourceIndex: index });
      return;
    }
    const rename = text.match(/(?:项目已重命名|Project renamed):\s*(.+?)\s*(?:→|->)\s*(.+)$/);
    if (rename) {
      events.push({ type: "rename", title: "项目重命名", detail: `${rename[1]} -> ${rename[2]}`, sourceIndex: index });
      return;
    }
    const step = text.match(/步骤\s+([0-9a-zA-Z]+)\s+(.+?)(?:\s+(RUN|DRY)\s+会话\s+(.+))?$/);
    if (step) {
      events.push({ type: "step", title: `步骤 ${step[1]} · ${step[2].trim()}`, detail: step[4] ? `会话 ${step[4]}` : undefined, sourceIndex: index });
      return;
    }
    if (/会话\s+\d+\s+·|第\s*\d+\s*幕|轮次|步骤\s+05b\s+循环|开篇创作|世界观|故事主轴|创意方案/.test(text)) {
      events.push({ type: "section", title: text, sourceIndex: index });
      return;
    }
    if (/完成|工作流完成|已生成|已创建|已追加|已选择|提取到|提取幕次|各幕章节数/.test(text)) {
      events.push({ type: "success", title: text, sourceIndex: index });
      return;
    }
    if (/警告|失败|failed|error|traceback|拒绝访问/i.test(text)) {
      events.push({ type: /警告|warn/i.test(text) ? "warning" : "error", title: text, sourceIndex: index });
      return;
    }
    if (/生成方案|干运行|自动继续|继续下一轮|当前轮次|断点定位|RUN|DRY/.test(text)) {
      events.push({ type: "note", title: text, sourceIndex: index });
    }
  });
  return events.slice(-120);
}

function App() {
  const [page, setPageState] = useState<Page>(() => {
    if (typeof window === "undefined") return "projects";
    const stored = localStorage.getItem("woke_novel_page") as Page | null;
    return stored && ["projects", "workbench", "assets", "chapters", "export", "logs", "settings"].includes(stored) ? stored : "projects";
  });
  const [selectedProject, setSelectedProjectState] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem("woke_novel_project") || "";
  });
  const [chapterToOpen, setChapterToOpen] = useState<string>("");
  const [assetToOpen, setAssetToOpen] = useState<string>("");
  const [runLogs, setRunLogs] = useState<Record<string, RunLogState>>({});
  const [search, setSearch] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "light";
    return localStorage.getItem("woke_novel_theme") === "dark" ? "dark" : "light";
  });
  const projects = useQuery({
    queryKey: ["projects", search],
    queryFn: () => api<{ items: ProjectSummary[]; total: number }>(`/projects${search ? `?q=${encodeURIComponent(search)}` : ""}`),
    refetchInterval: 3000
  });
  const environment = useQuery({ queryKey: ["environment"], queryFn: () => api<any>("/environment"), refetchInterval: 30000 });
  const activeProject = projects.data?.items.find((item) => item.project_name === selectedProject) || projects.data?.items[0];
  const selectedProjectExists = projects.data?.items.some((item) => item.project_name === selectedProject) || false;
  const setPage = useCallback((next: Page) => {
    setPageState(next);
    localStorage.setItem("woke_novel_page", next);
  }, []);
  const setSelectedProject = useCallback((project: string) => {
    setSelectedProjectState(project);
    if (project) localStorage.setItem("woke_novel_project", project);
    else localStorage.removeItem("woke_novel_project");
  }, []);

  useEffect(() => {
    if (activeProject && (!selectedProject || !selectedProjectExists)) setSelectedProject(activeProject.project_name);
    if (!activeProject && selectedProject) setSelectedProject("");
  }, [activeProject, selectedProject, selectedProjectExists]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("woke_novel_theme", theme);
  }, [theme]);

  const updateSelectedProjectLog = useCallback((updater: (current: RunLogState) => RunLogState) => {
    setRunLogs((current) => {
      const previous = current[selectedProject] || { run: null, lines: [], updatedAt: null, replaySkip: [] };
      return { ...current, [selectedProject]: updater(previous) };
    });
  }, [selectedProject]);

  const moveProjectLog = useCallback((from: string, to: string) => {
    if (!from || !to || from === to) return;
    setRunLogs((current) => {
      const existing = current[from];
      if (!existing) return current;
      const next = { ...current, [to]: existing };
      delete next[from];
      return next;
    });
  }, []);

  const nav = [
    ["projects", LayoutDashboard, "项目"],
    ["workbench", Gauge, "工作台"],
    ["assets", FolderTree, "创作资产"],
    ["chapters", BookOpen, "章节"],
    ["export", Download, "导出"],
    ["logs", Terminal, "日志"],
    ["settings", Settings, "设置"]
  ] as const;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <img className="brand-mark" src="/logo.png" alt="woke_novel logo" />
          <div>
            <strong>woke_novel</strong>
            <span>小说创作指挥中枢</span>
          </div>
        </div>
        <div className="project-switcher">
          <span>当前项目</span>
          <select value={selectedProject} onChange={(event) => setSelectedProject(event.target.value)}>
            {projects.data?.items.map((item) => (
              <option key={item.project_name} value={item.project_name}>
                {item.novel_name || item.project_name}
              </option>
            ))}
          </select>
        </div>
        <div className="top-search">
          <Search size={16} />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索项目、题材、小说名" />
        </div>
        <div className="backend-status">
          <span className={environment.data?.claude?.available ? "pill ok" : "pill warn"}>Claude</span>
          <span className={environment.data?.codex?.available ? "pill ok" : "pill warn"}>Codex</span>
          <button
            className="icon-button theme-toggle"
            type="button"
            title={theme === "dark" ? "切换日间模式" : "切换夜间模式"}
            aria-label={theme === "dark" ? "切换日间模式" : "切换夜间模式"}
            onClick={() => setTheme((current) => current === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
          </button>
        </div>
      </header>

      <aside className="sidebar">
        <nav>
          {nav.map(([key, Icon, label]) => (
            <button key={key} className={page === key ? "nav-item active" : "nav-item"} onClick={() => setPage(key)}>
              <Icon size={18} />
              <span>{label}</span>
              {key === "workbench" && activeProject?.status === "running" ? <i className="pulse-dot" /> : null}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span>D:/woke_novel</span>
          <strong>127.0.0.1</strong>
        </div>
      </aside>

      <main className="content">
        {page === "projects" && (
          <ProjectsPage
            projects={projects.data?.items || []}
            loading={projects.isLoading}
            selected={selectedProject}
            onSelect={setSelectedProject}
            onOpen={(project) => {
              setSelectedProject(project);
              setPage("workbench");
            }}
          />
        )}
        {page === "workbench" && (
          <WorkbenchPage
            project={selectedProject}
            logState={runLogs[selectedProject] || { run: null, lines: [], updatedAt: null, replaySkip: [] }}
            onLogStateChange={updateSelectedProjectLog}
            onProjectLogMove={moveProjectLog}
            onProjectChange={setSelectedProject}
            onOpenAsset={(path) => {
              setAssetToOpen(projectRelativePath(selectedProject, path));
              setPage("assets");
            }}
            onOpenChapter={(path) => {
              setChapterToOpen(path);
              setPage("chapters");
            }}
          />
        )}
        {page === "assets" && <AssetsPage project={selectedProject} initialFile={assetToOpen} onInitialFileUsed={() => setAssetToOpen("")} />}
        {page === "chapters" && <ChaptersPage project={selectedProject} initialFile={chapterToOpen} onInitialFileUsed={() => setChapterToOpen("")} />}
        {page === "export" && <ExportPage project={selectedProject} />}
        {page === "logs" && <LogsPage project={selectedProject} />}
        {page === "settings" && <SettingsPage environment={environment.data} />}
      </main>
    </div>
  );
}

function ProjectsPage({
  projects,
  loading,
  selected,
  onSelect,
  onOpen
}: {
  projects: ProjectSummary[];
  loading: boolean;
  selected: string;
  onSelect: (project: string) => void;
  onOpen: (project: string) => void;
}) {
  const [showCreate, setShowCreate] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ProjectSummary | null>(null);
  const totals = useMemo(
    () => ({
      running: projects.filter((item) => item.status === "running").length,
      continuable: projects.filter((item) => canProjectContinue(item) && item.status !== "running").length,
      chapters: projects.reduce((sum, item) => sum + item.chapter_progress.generated, 0)
    }),
    [projects]
  );

  return (
    <section className="page">
      <div className={showCreate ? "page-blur-layer blurred" : "page-blur-layer"}>
        <div className="page-head">
          <div>
            <h1>项目总览</h1>
            <p>查看项目进度、断点、章节和最近状态。</p>
          </div>
          <button className="primary-button" onClick={() => setShowCreate(true)}>
            <Plus size={16} /> 新建项目
          </button>
        </div>

        <div className="status-strip">
          <Metric label="项目" value={projects.length} />
          <Metric label="运行中" value={totals.running} />
          <Metric label="可续写" value={totals.continuable} tone={totals.continuable ? "warn" : "ok"} />
          <Metric label="已生成章节" value={totals.chapters} />
        </div>

        <div className="table-surface">
          <table>
            <thead>
              <tr>
                <th>项目 / 小说</th>
                <th>题材</th>
                <th>阶段</th>
                <th>章节</th>
                <th>最后步骤</th>
                <th>状态</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td className="table-empty" colSpan={7}><span className="loading-text"><Loader2 className="spin" size={16} /> 正在扫描项目...</span></td></tr>
              ) : projects.length === 0 ? (
                <tr><td className="table-empty" colSpan={7}>暂无项目，创建一个项目开始工作流。</td></tr>
              ) : (
                projects.map((project) => (
                  <tr
                    key={project.project_name}
                    className={selected === project.project_name ? "selected-row clickable-row" : "clickable-row"}
                    onClick={() => onSelect(project.project_name)}
                    onDoubleClick={() => onOpen(project.project_name)}
                  >
                    <td>
                      <strong>{project.novel_name || "未命名"}</strong>
                      <span>{project.project_name}</span>
                    </td>
                    <td>{project.genre}</td>
                    <td>
                      <Progress value={project.progress_percent} label={project.stage} />
                    </td>
                    <td>{project.chapter_progress.generated} / {project.chapter_progress.target || "?"}</td>
                    <td>{project.last_step ? `${project.last_step} ${project.last_step_name}` : "未开始"}</td>
                    <td>
                      <span className={statusClass(project)}>{statusLabel(project)}</span>
                      {project.status === "running" && project.run_pid ? <small className="run-source">PID {project.run_pid}</small> : null}
                    </td>
                    <td>
                      <div className="table-actions">
                      <button className="ghost-button" onClick={(event) => { event.stopPropagation(); onOpen(project.project_name); }}>
                        打开 <ChevronRight size={15} />
                      </button>
                        <button className="icon-button danger-button" title="删除项目" onClick={(event) => { event.stopPropagation(); setDeleteTarget(project); }} disabled={project.status === "running"}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate ? <CreateProjectDialog existingProjects={projects.map((item) => item.project_name)} onClose={() => setShowCreate(false)} /> : null}
      {deleteTarget ? <DeleteProjectDialog project={deleteTarget} onClose={() => setDeleteTarget(null)} /> : null}
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone?: "ok" | "warn" }) {
  return (
    <div className={`metric ${tone || ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Progress({ value, label }: { value: number; label: string }) {
  return (
    <div className="progress-cell">
      <span>{label}</span>
      <div className="progress-track"><i style={{ width: `${Math.max(4, value)}%` }} /></div>
    </div>
  );
}

function DeleteProjectDialog({ project, onClose }: { project: ProjectSummary; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [confirmText, setConfirmText] = useState("");
  const [deleteLogs, setDeleteLogs] = useState(true);
  const canDelete = confirmText === project.project_name;
  const removeProject = useMutation({
    mutationFn: () =>
      api(`/projects/${encodeURIComponent(project.project_name)}/delete`, {
        method: "POST",
        body: JSON.stringify({ confirm_text: confirmText, delete_logs: deleteLogs })
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      onClose();
    }
  });

  return (
    <div className="dialog-backdrop">
      <div className="dialog delete-dialog">
        <div className="dialog-head">
          <div>
            <h2><Trash2 size={18} /> 删除项目</h2>
            <p>删除后会移除项目目录，已生成正文、状态文档和项目元数据都会被清除。</p>
          </div>
          <button className="icon-button" onClick={onClose}>×</button>
        </div>
        <div className="delete-body">
          <div className="danger-summary">
            <strong>{project.novel_name || project.project_name}</strong>
            <span>{project.project_name}</span>
          </div>
          <label className="checkbox-line">
            <input type="checkbox" checked={deleteLogs} onChange={(event) => setDeleteLogs(event.target.checked)} />
            同时删除该项目日志
          </label>
          <label>
            输入项目名称确认删除
            <input value={confirmText} onChange={(event) => setConfirmText(event.target.value)} placeholder={project.project_name} />
          </label>
          {removeProject.error ? <InlineError message={removeProject.error.message} /> : null}
        </div>
        <div className="dialog-actions">
          <button className="ghost-button" onClick={onClose}>取消</button>
          <button className="primary-button danger-primary" onClick={() => removeProject.mutate()} disabled={!canDelete || removeProject.isPending}>
            {removeProject.isPending ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />} 删除
          </button>
        </div>
      </div>
    </div>
  );
}

function CreateProjectDialog({ existingProjects, onClose }: { existingProjects: string[]; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [genreSearch, setGenreSearch] = useState("");
  const [genreChannel, setGenreChannel] = useState("");
  const [genreType, setGenreType] = useState("");
  const [selectedPreset, setSelectedPreset] = useState<GenrePreset | null>(null);
  const [form, setForm] = useState({
    project_name: "",
    genre: "都市",
    language: "zh",
    provider: "claude",
    novel_size: "中篇",
    option_count: 3,
    dry_run: false,
    start_immediately: true,
    user_description: ""
  });
  const genrePresets = useQuery({
    queryKey: ["genre-presets", form.language],
    queryFn: () => api<{ items: GenrePreset[]; total: number }>(`/genre-presets?language=${form.language}`)
  });
  const genreChannels = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of genrePresets.data?.items || []) {
      map.set(item.channel_id, item.channel_name);
    }
    return Array.from(map, ([id, name]) => ({ id, name }));
  }, [genrePresets.data?.items]);
  const genreTypes = useMemo(() => {
    const map = new Map<string, { id: string; name: string; channelId: string }>();
    for (const item of genrePresets.data?.items || []) {
      if (genreChannel && item.channel_id !== genreChannel) continue;
      map.set(item.genre_id, { id: item.genre_id, name: item.genre_name, channelId: item.channel_id });
    }
    return Array.from(map.values());
  }, [genreChannel, genrePresets.data?.items]);
  const filteredGenres = useMemo(() => {
    const needle = genreSearch.trim().toLowerCase();
    const items = genrePresets.data?.items || [];
    return items.filter((item) => {
      if (genreChannel && item.channel_id !== genreChannel) return false;
      if (genreType && item.genre_id !== genreType) return false;
      if (!needle) return true;
      return `${item.channel_name} ${item.genre_name} ${item.theme_name} ${item.description}`.toLowerCase().includes(needle);
    });
  }, [genreChannel, genrePresets.data?.items, genreSearch, genreType]);
  const create = useMutation({
    mutationFn: () => api("/projects", { method: "POST", body: JSON.stringify({ ...form, auto_select_option: 1 }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      onClose();
    }
  });
  const normalizedProjectName = form.project_name.trim();
  const projectNameExists = existingProjects.some((name) => name.toLowerCase() === normalizedProjectName.toLowerCase());
  const selectedSize = NOVEL_SIZE_OPTIONS.find((item) => item.value === form.novel_size);
  const commandName = form.option_count > 1 ? "creative" : "loop";
  const command = `python run_workflow.py ${commandName} --project-name ${form.project_name || "<project>"} --genre ${form.genre} --language ${form.language} --provider ${form.provider} --option-count ${form.option_count}${form.dry_run ? " --dry" : ""}`;
  const selectGenre = (preset: GenrePreset) => {
    setSelectedPreset(preset);
    setForm({ ...form, genre: preset.genre_name, user_description: preset.description });
  };

  return (
    <div className="dialog-backdrop">
      <div className="dialog">
        <div className="dialog-head">
          <div>
            <h2>新建项目</h2>
            <p>在一个界面中完成项目、模型、题材、规模和运行策略配置。</p>
          </div>
          <button className="icon-button" onClick={onClose}>×</button>
        </div>
        <div className="create-form">
          <div className="config-section">
            <div className="section-title">
              <strong>基础信息</strong>
              <span>决定项目目录、题材和创作模板语言。</span>
            </div>
            <div className="form-grid">
              <label>
                项目名称
                <input className={projectNameExists ? "input-error" : ""} value={form.project_name} onChange={(e) => setForm({ ...form, project_name: e.target.value })} />
                {projectNameExists ? <span className="field-error">项目名称已存在，请换一个名称。</span> : null}
              </label>
              <label>语言<select value={form.language} onChange={(e) => { setSelectedPreset(null); setGenreSearch(""); setGenreChannel(""); setGenreType(""); setForm({ ...form, language: e.target.value, genre: e.target.value === "en" ? "Fantasy" : "都市", user_description: "" }); }}><option value="zh">中文</option><option value="en">English</option></select></label>
              <label>
                小说规模
                <select value={form.novel_size} onChange={(e) => setForm({ ...form, novel_size: e.target.value })}>
                  {NOVEL_SIZE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label} · {item.words}</option>)}
                </select>
                <span className="field-hint">{selectedSize?.words}</span>
              </label>
              <label>当前题材<input value={form.genre} onChange={(e) => { setSelectedPreset(null); setForm({ ...form, genre: e.target.value }); }} /></label>
              <div className="genre-picker full">
                <div className="genre-search">
                  <Search size={16} />
                  <input value={genreSearch} onChange={(e) => setGenreSearch(e.target.value)} placeholder="搜索频道、题材或细分主题" />
                </div>
                <div className="genre-level">
                  <span>频道</span>
                  <button type="button" className={!genreChannel ? "active" : ""} onClick={() => { setGenreChannel(""); setGenreType(""); }}>全部频道</button>
                  {genreChannels.map((channel) => (
                    <button key={channel.id} type="button" className={genreChannel === channel.id ? "active" : ""} onClick={() => { setGenreChannel(channel.id); setGenreType(""); }}>
                      {channel.name}
                    </button>
                  ))}
                </div>
                <div className="genre-level">
                  <span>类型</span>
                  <button type="button" className={!genreType ? "active" : ""} onClick={() => setGenreType("")}>全部类型</button>
                  {genreTypes.map((genre) => (
                    <button key={`${genre.channelId}.${genre.id}`} type="button" className={genreType === genre.id ? "active" : ""} onClick={() => setGenreType(genre.id)}>
                      {genre.name}
                    </button>
                  ))}
                </div>
                {selectedPreset ? (
                  <div className="selected-genre">
                    <strong>{selectedPreset.genre_name} · {selectedPreset.theme_name}</strong>
                    <span>{selectedPreset.description}</span>
                  </div>
                ) : null}
                <div className="genre-count">已展示 {filteredGenres.length} / {genrePresets.data?.total || 0} 个细分主题</div>
                <div className="genre-grid">
                  {filteredGenres.map((preset) => (
                    <button key={preset.id} type="button" className={selectedPreset?.id === preset.id ? "genre-card active" : "genre-card"} onClick={() => selectGenre(preset)}>
                      <span>{preset.channel_name}</span>
                      <strong>{preset.genre_name} · {preset.theme_name}</strong>
                      <em>{preset.description}</em>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="config-section">
            <div className="section-title">
              <strong>运行配置</strong>
              <span>控制模型后端、创意方案数量和是否立即运行。</span>
            </div>
            <div className="form-grid">
              <label>后端<select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })}><option value="claude">Claude CLI</option><option value="codex">Codex CLI</option></select></label>
              <label>创意方案数<input type="number" min={1} max={10} value={form.option_count} onChange={(e) => setForm({ ...form, option_count: Number(e.target.value) })} /></label>
              <div className="toggle-row full">
                <label><input type="checkbox" checked={form.dry_run} onChange={(e) => setForm({ ...form, dry_run: e.target.checked })} /> 干运行</label>
                <label><input type="checkbox" checked={form.start_immediately} onChange={(e) => setForm({ ...form, start_immediately: e.target.checked })} /> 创建后启动</label>
              </div>
            </div>
          </div>

          <div className="config-section">
            <div className="section-title">
              <strong>创作补充</strong>
              <span>补充说明会传给完整工作流的创意生成阶段。</span>
            </div>
            <div className="form-grid">
              <label className="full">补充说明<textarea value={form.user_description} onChange={(e) => setForm({ ...form, user_description: e.target.value })} /></label>
            </div>
          </div>

          <div className="config-section command-section">
            <div className="section-title">
              <strong>等效命令</strong>
              <span>多方案会先停在创意选择；选定方案后继续执行，后续可能按小说名重命名项目目录。</span>
            </div>
            <code className="command-preview">{command}</code>
          </div>
          {projectNameExists ? <p className="error-text">当前项目目录已存在，不能重复创建。</p> : null}
          {create.error ? <p className="error-text">{create.error.message}</p> : null}
        </div>
        <div className="dialog-actions">
          <button className="ghost-button" onClick={onClose}>取消</button>
          <button className="primary-button" onClick={() => create.mutate()} disabled={!normalizedProjectName || projectNameExists || create.isPending}>
            {create.isPending ? <Loader2 className="spin" size={16} /> : <Plus size={16} />} 创建
          </button>
        </div>
      </div>
    </div>
  );
}

function WorkbenchPage({
  project,
  logState,
  onLogStateChange,
  onProjectLogMove,
  onProjectChange,
  onOpenAsset,
  onOpenChapter
}: {
  project: string;
  logState: RunLogState;
  onLogStateChange: (updater: (current: RunLogState) => RunLogState) => void;
  onProjectLogMove: (from: string, to: string) => void;
  onProjectChange: (project: string) => void;
  onOpenAsset: (path: string) => void;
  onOpenChapter: (path: string) => void;
}) {
  const queryClient = useQueryClient();
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const lastRunLogRefreshRef = useRef(0);
  const run = logState.run;
  const lines = logState.lines;
  const [logView, setLogView] = useState<"events" | "raw">("events");
  const [historySuppressed, setHistorySuppressed] = useState(false);
  const detail = useQuery({ queryKey: ["project", project], queryFn: () => api<any>(`/projects/${project}`), enabled: Boolean(project), refetchInterval: 5000 });
  const historicalLogs = useQuery({
    queryKey: ["logs", project, "workbench-history"],
    queryFn: () => api<{ items: LogEntry[] }>(`/projects/${project}/logs`),
    enabled: Boolean(project),
    refetchInterval: run ? 3000 : false
  });
  const runLogEntry = historicalLogs.data?.items.find((item) => item.log_id === "run.log");
  const creativeOptions = useQuery({
    queryKey: ["creative-options", project],
    queryFn: () => api<{ items: CreativeOption[]; total: number }>(`/projects/${project}/creative-options`),
    enabled: Boolean(project && detail.data?.info?.last_step === "01" && !detail.data?.info?.selected_option),
    refetchInterval: 5000
  });
  const [fullRun, setFullRun] = useState({
    language: "zh",
    provider: "claude",
    dry_run: false,
    option_count: 3,
    auto_select_option: 1,
    max_retries: 3,
    user_description: ""
  });
  const runMutation = useMutation({
    mutationFn: ({ mode, body }: { mode: "creative" | "full" | "continue"; body: Record<string, unknown> }) => api<RunRecord>(`/projects/${project}/runs/${mode}`, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: (record) => {
      setHistorySuppressed(false);
      onLogStateChange(() => ({
        run: record,
        lines: [],
        updatedAt: new Date().toISOString(),
        replaySkip: []
      }));
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    }
  });
  const cancelRun = useMutation({
    mutationFn: () => api(`/projects/${project}/runs/cancel`, { method: "POST" }),
    onSuccess: () => {
      onLogStateChange((current) => ({
        ...current,
        run: null,
        updatedAt: new Date().toISOString(),
        replaySkip: []
      }));
      queryClient.invalidateQueries({ queryKey: ["project", project] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      const now = Date.now();
      if (now - lastRunLogRefreshRef.current > 1000) {
        lastRunLogRefreshRef.current = now;
        queryClient.invalidateQueries({ queryKey: ["logs", project] });
      }
    }
  });
  const selectCreative = useMutation({
    mutationFn: (optionIndex: number) =>
      api(`/projects/${project}/creative-options/select`, {
        method: "POST",
        body: JSON.stringify({ option_index: optionIndex })
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", project] });
      queryClient.invalidateQueries({ queryKey: ["creative-options", project] });
      runMutation.mutate({
        mode: "continue",
        body: { language: fullRun.language, provider: fullRun.provider, dry_run: fullRun.dry_run, max_retries: fullRun.max_retries }
      });
    }
  });

  useEffect(() => {
    if (!detail.data?.info) return;
    const info = detail.data.info;
    setFullRun((current) => ({
      ...current,
      language: info.language || current.language,
      provider: info.provider || current.provider,
      option_count: info.option_count || current.option_count,
      auto_select_option: info.auto_select_option || info.selected_option || current.auto_select_option,
      user_description: info.user_description || current.user_description
    }));
  }, [detail.data?.info?.project_name]);

  useEffect(() => {
    if (!project || historySuppressed) return;
    let cancelled = false;
    const loadRunLog = async () => {
      if (!runLogEntry) {
        onLogStateChange((current) => {
          if (!current.lines.length) return current;
          return { ...current, lines: [], updatedAt: new Date().toISOString(), replaySkip: [] };
        });
        return;
      }
      let restored: string[] = [];
      try {
        const log = await api<{ content: string }>(`/projects/${project}/logs/run.log?tail=500`);
        restored = log.content ? log.content.split(/\r?\n/) : [];
      } catch {
        restored = [];
      }
      if (cancelled) return;
      onLogStateChange((current) => {
        if (current.lines.join("\n") === restored.join("\n")) return current;
        return {
        ...current,
        lines: restored,
        updatedAt: new Date().toISOString(),
        replaySkip: []
        };
      });
    };
    loadRunLog();
    return () => {
      cancelled = true;
    };
  }, [historySuppressed, onLogStateChange, project, runLogEntry?.size, runLogEntry?.updated_at]);

  useEffect(() => {
    const latestRun = detail.data?.latest_run as RunRecord | null | undefined;
    if (!project || !latestRun || run?.run_id === latestRun.run_id) return;
    onLogStateChange((current) => ({
      ...current,
      run: latestRun,
      updatedAt: new Date().toISOString(),
      replaySkip: []
    }));
  }, [detail.data?.latest_run, onLogStateChange, project, run?.run_id]);

  useEffect(() => {
    if (!run) return undefined;
    const source = new EventSource(`${API}/projects/${project}/runs/${run.run_id}/events`);
    source.addEventListener("log_line", (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      if (!data?.line) return;
      onLogStateChange((current) => {
        const replaySkip = current.replaySkip || [];
        if (replaySkip.length) {
          const matchIndex = replaySkip.indexOf(data.line);
          if (matchIndex >= 0) {
            return { ...current, replaySkip: replaySkip.slice(matchIndex + 1), updatedAt: new Date().toISOString() };
          }
        }
        return { ...current, updatedAt: new Date().toISOString(), replaySkip };
      });
      queryClient.invalidateQueries({ queryKey: ["logs", project] });
    });
    source.addEventListener("run_succeeded", () => {
      onLogStateChange((current) => ({
        ...current,
        run: null,
        updatedAt: new Date().toISOString(),
        replaySkip: []
      }));
      queryClient.invalidateQueries({ queryKey: ["project", project] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["logs", project] });
      queryClient.invalidateQueries({ queryKey: ["creative-options", project] });
      source.close();
    });
    source.addEventListener("project_renamed", (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      if (data.to) {
        onProjectLogMove(data.from || project, data.to);
        onProjectChange(data.to);
        queryClient.invalidateQueries({ queryKey: ["projects"] });
        queryClient.invalidateQueries({ queryKey: ["project", data.to] });
      }
    });
    source.addEventListener("run_failed", (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      onLogStateChange((current) => ({
        ...current,
        run: null,
        updatedAt: new Date().toISOString(),
        replaySkip: []
      }));
      queryClient.invalidateQueries({ queryKey: ["project", project] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["logs", project] });
      source.close();
    });
    source.addEventListener("run_cancelled", () => {
      onLogStateChange((current) => ({
        ...current,
        run: null,
        updatedAt: new Date().toISOString(),
        replaySkip: []
      }));
      queryClient.invalidateQueries({ queryKey: ["project", project] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["logs", project] });
      source.close();
    });
    return () => source.close();
  }, [onLogStateChange, onProjectChange, onProjectLogMove, project, queryClient, run]);

  useEffect(() => {
    if (!terminalRef.current) return;
    terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [lines.length]);

  const info = detail.data?.info;
  const workflow = detail.data?.workflow;
  const expectedCreativeCount = Number(info?.option_count || creativeOptions.data?.total || 0);
  const generatedCreativeCount = (creativeOptions.data?.items || []).filter((option) => option.exists).length;
  const allCreativeOptionsReady = expectedCreativeCount > 0 && generatedCreativeCount >= expectedCreativeCount;
  const awaitingCreativeChoice = Boolean(info?.last_step === "01" && !info?.selected_option && allCreativeOptionsReady);
  const generatingCreativeOptions = Boolean(info?.last_step === "01" && !info?.selected_option && !allCreativeOptionsReady);
  const currentStep = workflow?.current_step;
  const latestArtifacts = detail.data?.latest_artifacts || [];
  const activeRun = run || detail.data?.latest_run;
  const chapterTotal = detail.data?.chapter_progress?.target || (Array.isArray(info?.chapter_counts) ? info.chapter_counts.reduce((sum: number, count: number) => sum + count, 0) : info?.total_chapters);
  const generatedChapters = detail.data?.chapter_progress?.generated || 0;
  const projectHasStarted = Boolean(info?.last_step);
  const chapterTargetMet = Boolean(chapterTotal && generatedChapters >= chapterTotal);
  const projectRunning = workflow?.overall_status === "running" || workflow?.overall_status === "queued";
  const runSourceLabel = workflow?.run_source === "cli" ? "CLI" : workflow?.run_source === "api" ? "前端" : "未运行";
  const shouldShowCreativeStart = !projectHasStarted && !chapterTargetMet;
  const shouldShowContinue = projectHasStarted && !chapterTargetMet && !awaitingCreativeChoice;
  const currentRound = currentStep?.round_num || info?.current_round || 1;
  const currentAct = currentStep?.act_num || info?.last_step_act;
  const actTotal = info?.act_count;
  const actLabel = currentAct && actTotal ? `${currentAct} / ${actTotal}` : currentAct || actTotal || "未记录";
  const nextActionLabel = awaitingCreativeChoice ? "选择创意方案" : workflow?.next_action?.label || "启动完整工作流";
  const runningStepLabel = currentStep?.step ? `${currentStep.step} ${currentStep.name || ""}`.trim() : `${runSourceLabel} 正在运行${workflow?.run_pid ? ` · PID ${workflow.run_pid}` : ""}`;
  const progressValue = chapterTotal ? Math.min(100, Math.round((generatedChapters / chapterTotal) * 100)) : 0;
  const parsedEvents = useMemo(() => parseLogEvents(lines), [lines]);
  const stepOrder = useMemo(() => ["01", "02", "03", "04", "05", "05a", "05b", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18"], []);
  const lastStepIndex = info?.last_step ? stepOrder.indexOf(info.last_step) : -1;
  const currentStepCode = currentStep?.step || info?.last_step;
  const statusForStep = (code: string): TimelineStepStatus => {
    const index = stepOrder.indexOf(code);
    if (projectRunning && currentStepCode === code) return "running";
    if (index >= 0 && lastStepIndex >= index) return "succeeded";
    return "not_started";
  };
  const linearTimeline = LINEAR_WORKFLOW_SECTIONS.map((section) => {
    const steps: TimelineStep[] = section.steps.map(([code, name]) => ({ code, name, status: statusForStep(code) }));
    const status = steps.some((step) => step.status === "running")
      ? "running"
      : steps.every((step) => step.status === "succeeded")
        ? "succeeded"
        : steps.some((step) => step.status === "succeeded")
          ? "running"
          : "not_started";
    return { ...section, status: status as TimelineStepStatus, steps };
  });
  const loopStepCodes = new Set(LOOP_WORKFLOW_STEPS.map(([code]) => code));
  const actEndStepCodes = new Set(ACT_END_WORKFLOW_STEPS.map(([code]) => code));
  const loopActive = Boolean(currentStepCode && (loopStepCodes.has(currentStepCode) || actEndStepCodes.has(currentStepCode)));
  const loopStarted = lastStepIndex >= stepOrder.indexOf("11") || generatedChapters > 1;
  const loopComplete = Boolean(chapterTargetMet && generatedChapters > 0);
  const loopStatus: TimelineStepStatus = projectRunning && loopActive ? "running" : loopComplete ? "succeeded" : loopStarted ? "running" : "not_started";
  const loopTimelineSteps: TimelineStep[] = LOOP_WORKFLOW_STEPS.map(([code, name]) => ({
    code,
    name,
    status: projectRunning && currentStepCode === code ? "running" : loopStarted ? "succeeded" : "not_started"
  }));
  const actEndTimelineSteps: TimelineStep[] = ACT_END_WORKFLOW_STEPS.map(([code, name]) => ({
    code,
    name,
    status: projectRunning && currentStepCode === code ? "running" : actEndStepCodes.has(info?.last_step || "") ? "succeeded" : "not_started"
  }));

  if (!project) return <EmptyState title="未选择项目" />;

  return (
    <section className="page workbench-page">
      <div className="workbench-head">
        <div>
          <h1>{info?.novel_name || project}</h1>
          <p>{project} · {info?.genre || "未知题材"} · {info?.novel_size || "未设置"} · {info?.provider || "claude"}</p>
        </div>
        {(shouldShowCreativeStart || shouldShowContinue || projectRunning) ? (
          <div className="action-row">
            {shouldShowContinue ? (
              <button className="primary-button" onClick={() => runMutation.mutate({ mode: "continue", body: { language: fullRun.language, provider: fullRun.provider, dry_run: fullRun.dry_run, max_retries: fullRun.max_retries } })} disabled={runMutation.isPending || projectRunning}>
                {runMutation.isPending || projectRunning ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />} {projectRunning ? "运行中" : "继续生成"}
              </button>
            ) : null}
            {shouldShowCreativeStart ? (
              <button className="primary-button" onClick={() => runMutation.mutate({ mode: "creative", body: { ...fullRun, genre: info?.genre || "都市", novel_size: info?.novel_size || "中篇" } })} disabled={runMutation.isPending || awaitingCreativeChoice || projectRunning}>
                {runMutation.isPending || projectRunning ? <Loader2 className="spin" size={16} /> : <Play size={16} />} {projectRunning ? "运行中" : "生成创意候选"}
              </button>
            ) : null}
            {projectRunning && !shouldShowContinue && !shouldShowCreativeStart ? (
              <button className="primary-button" disabled>
                <Loader2 className="spin" size={16} /> 运行中
              </button>
            ) : null}
            {projectRunning ? (
              <button className="stop-run-button" title="停止运行" onClick={() => cancelRun.mutate()} disabled={cancelRun.isPending}>
                {cancelRun.isPending ? <Loader2 className="spin" size={15} /> : <Square size={14} fill="currentColor" />}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="workbench-summary">
        <div className="summary-main">
          <div className="summary-title">
            <span className={`run-dot ${workflow?.overall_status || "idle"}`} />
            <strong>{runStatusLabel(workflow?.overall_status)}</strong>
            <span>{projectRunning ? runningStepLabel : nextActionLabel}</span>
          </div>
          <div className="summary-progress">
            <div><i style={{ width: `${progressValue}%` }} /></div>
            <span>{generatedChapters} / {chapterTotal || "?"}</span>
          </div>
        </div>
        <div className="summary-stat">
          <Clock3 size={17} />
          <span>当前轮次</span>
          <strong>R{currentRound}</strong>
        </div>
        <div className="summary-stat">
          <Gauge size={17} />
          <span>幕次</span>
          <strong>{actLabel}</strong>
        </div>
        <div className="summary-stat">
          <BookOpen size={17} />
          <span>章节进度</span>
          <strong>{progressValue}%</strong>
        </div>
      </div>

      <div className="timeline timeline-detailed">
        <div className="linear-flow">
          {linearTimeline.map((section) => (
            <div key={section.key} className={`stage detailed-stage ${section.status}`}>
              <div className="stage-head">
                <span>{section.name}</span>
                <i>{workflowStatusLabel(section.status)}</i>
              </div>
              <em>{section.note}</em>
              <div className="step-chain">
                {section.steps.map((step) => (
                  <span key={step.code} className={`step-pill ${step.status}`}>
                    <b>{step.code}</b>{step.name}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className={`stage loop-stage ${loopStatus}`}>
          <div className="stage-head">
            <span>正文循环</span>
            <i>{loopComplete ? "章节目标已达成" : loopStarted ? "按轮次循环中" : "未开始"}</i>
          </div>
          <div className="loop-summary">
            <div><span>当前轮次</span><strong>R{currentRound}</strong></div>
            <div><span>章节进度</span><strong>{generatedChapters} / {chapterTotal || "?"}</strong></div>
            <div><span>当前幕次</span><strong>{actLabel}</strong></div>
          </div>
          <div className="loop-progress">
            <div><i style={{ width: `${progressValue}%` }} /></div>
            <span>{progressValue}%</span>
          </div>
          <div className="loop-step-groups">
            <div>
              <strong>每轮步骤</strong>
              <div className="step-chain">
                {loopTimelineSteps.map((step) => (
                  <span key={step.code} className={`step-pill ${step.status}`}>
                    <b>{step.code}</b>{step.name}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <strong>幕末收束</strong>
              <div className="step-chain">
                {actEndTimelineSteps.map((step) => (
                  <span key={step.code} className={`step-pill ${step.status}`}>
                    <b>{step.code}</b>{step.name}
                  </span>
                ))}
              </div>
            </div>
          </div>
          <em>正文不是一次性阶段：11-16 会随章节反复执行，17/18 只在幕末收束时发生。</em>
        </div>
      </div>

      <div className="workbench-grid">
        <section className="panel task-panel">
          <h2><Gauge size={18} /> 当前任务</h2>
          <div className="kv-list">
            <span>当前步骤</span><strong>{currentStep?.step ? `${currentStep.step} ${currentStep.name}` : "未开始"}</strong>
            <span>运行来源</span><strong>{projectRunning ? `${runSourceLabel}${workflow?.run_pid ? ` · PID ${workflow.run_pid}` : ""}` : "空闲"}</strong>
            <span>下一步</span><strong>{nextActionLabel}</strong>
            <span>最后步骤</span><strong>{info?.last_step ? `${info.last_step} ${info.last_step_name || ""}` : "未记录"}</strong>
            <span>更新时间</span><strong>{formatTime(info?.last_step_at)}</strong>
          </div>
          <div className="task-actions">
            {shouldShowContinue ? (
              <button className="secondary-button" onClick={() => runMutation.mutate({ mode: "continue", body: { language: fullRun.language, provider: fullRun.provider, dry_run: fullRun.dry_run, max_retries: fullRun.max_retries } })} disabled={runMutation.isPending || projectRunning}>
                {projectRunning ? <Loader2 className="spin" size={16} /> : <RotateCcw size={16} />} {projectRunning ? "运行中" : "继续生成"}
              </button>
            ) : null}
            <button className="ghost-button" onClick={() => queryClient.invalidateQueries({ queryKey: ["project", project] })}>
              <RefreshCw size={16} /> 刷新
            </button>
          </div>
        </section>

        {shouldShowCreativeStart ? (
          <section className="panel project-config-panel">
            <h2><FileText size={18} /> 创建配置</h2>
            <div className="readonly-config">
              <div><span>项目名称</span><strong>{project}</strong></div>
              <div><span>小说名称</span><strong>{info?.novel_name || "未生成"}</strong></div>
              <div><span>题材</span><strong>{info?.genre || "未知题材"}</strong></div>
              <div><span>规模</span><strong>{info?.novel_size || "未设置"}</strong></div>
              <div><span>语言</span><strong>{info?.language === "en" ? "English" : "中文"}</strong></div>
              <div><span>后端</span><strong>{info?.provider || "claude"}</strong></div>
              <div><span>创意方案数</span><strong>{info?.option_count || fullRun.option_count}</strong></div>
              <div><span>自动选择</span><strong>{info?.auto_select_option || info?.selected_option || "未设置"}</strong></div>
              <div><span>干运行</span><strong>{info?.dry_run ? "是" : "否"}</strong></div>
              <div><span>创建后启动</span><strong>{info?.last_step ? "已启动" : "待启动"}</strong></div>
              <div className="wide"><span>补充说明</span><strong>{info?.user_description || "未填写"}</strong></div>
            </div>
          </section>
        ) : null}

        {shouldShowContinue ? (
          <section className="panel continue-panel">
            <h2><RefreshCw size={18} /> 继续生成</h2>
            <div className="continue-progress">
              <strong>{generatedChapters} / {chapterTotal || "?"}</strong>
              <span>当前章节进度</span>
              <div><i style={{ width: `${progressValue}%` }} /></div>
            </div>
            <button className="primary-button wide-button" onClick={() => runMutation.mutate({ mode: "continue", body: { language: fullRun.language, provider: fullRun.provider, dry_run: fullRun.dry_run, max_retries: fullRun.max_retries } })} disabled={runMutation.isPending || projectRunning}>
              {runMutation.isPending || projectRunning ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />} {projectRunning ? "运行中，暂不可操作" : "继续生成"}
            </button>
          </section>
        ) : null}

        <section className="panel artifacts-panel">
          <h2><FileText size={18} /> 最新产物</h2>
          <div className="artifact-list">
            {latestArtifacts.map((item: Chapter) => (
              <button key={item.relative_path} type="button" onClick={() => onOpenChapter(item.relative_path)}>
                <strong>{item.title}</strong>
                <span>{item.word_count} 字 · {formatTime(item.updated_at)}</span>
              </button>
            ))}
            {!latestArtifacts.length ? <p>暂无章节产物。</p> : null}
          </div>
        </section>

        {awaitingCreativeChoice ? (
          <section className="panel creative-choice-panel">
            <h2><ListChecks size={18} /> 选择创意方案</h2>
            <p>选择后会先补充该方案，再继续世界观、人物、主轴和正文流程。</p>
            <div className="creative-option-grid">
              {(creativeOptions.data?.items || []).map((option) => (
                <article key={option.index} className="creative-option-card">
                  <div className="creative-option-head">
                    <div>
                      <span>方案 {option.index}</span>
                      <strong>{option.title}</strong>
                    </div>
                    <button className="icon-button" title="查看详情" onClick={() => onOpenAsset(option.relative_path)} disabled={!option.exists}>
                      <FileText size={15} />
                    </button>
                  </div>
                  <p>{option.opening || "方案文件已生成，但未解析到开篇设想。"}</p>
                  <button className="primary-button" onClick={() => selectCreative.mutate(option.index)} disabled={!option.exists || selectCreative.isPending || runMutation.isPending}>
                    {selectCreative.isPending ? <Loader2 className="spin" size={16} /> : <CheckCircle2 size={16} />} 选择并继续
                  </button>
                </article>
              ))}
            </div>
            {creativeOptions.isLoading ? <p>正在读取创意方案...</p> : null}
            {selectCreative.error ? <InlineError message={selectCreative.error.message} /> : null}
          </section>
        ) : null}

        {generatingCreativeOptions ? (
          <section className="panel creative-choice-panel">
            <h2><Loader2 className="spin" size={18} /> 创意方案生成中</h2>
            <p>已生成 {generatedCreativeCount} / {expectedCreativeCount || "?"} 个方案，全部生成后会显示选择卡片。</p>
          </section>
        ) : null}

        <section className="panel log-panel">
          <div className="panel-title-row">
            <h2><Terminal size={18} /> 实时日志</h2>
            <div className="log-toolbar">
              <span>{activeRun?.run_id || "未运行"}</span>
              <span>{parsedEvents.length} 事件 · {lines.length} 行</span>
              <div className="segmented-control">
                <button className={logView === "events" ? "active" : ""} onClick={() => setLogView("events")}>事件</button>
                <button className={logView === "raw" ? "active" : ""} onClick={() => setLogView("raw")}>原始</button>
              </div>
              <button className="ghost-button compact-button" onClick={() => { setHistorySuppressed(true); onLogStateChange((current) => ({ ...current, lines: [], replaySkip: [], updatedAt: new Date().toISOString() })); }} disabled={!lines.length}>
                清空
              </button>
            </div>
          </div>
          {logView === "events" ? (
            <div className="event-log-frame" ref={terminalRef}>
              {parsedEvents.length ? (
                parsedEvents.map((event) => (
                  <div key={`${event.sourceIndex}-${event.title}`} className={`log-event ${event.type}`}>
                    <i />
                    <div>
                      <strong>{event.title}</strong>
                      {event.detail ? <span>{event.detail}</span> : null}
                    </div>
                    <em>#{event.sourceIndex + 1}</em>
                  </div>
                ))
              ) : (
                <div className="terminal-empty">
                  {projectRunning && workflow?.run_source === "cli"
                    ? "检测到终端 CLI 正在运行。前端可识别运行状态；实时 stdout 只对前端启动的任务可用，请在日志页查看落盘日志。"
                    : historicalLogs.isLoading
                      ? "正在读取历史流程事件..."
                      : "暂无可显示的流程事件。"}
                </div>
              )}
            </div>
          ) : (
            <div className="terminal-frame" ref={terminalRef}>
              {lines.length ? (
                lines.map((line, index) => (
                  <div key={`${index}-${line.slice(0, 20)}`} className={`terminal-line ${line.toLowerCase().includes("failed") || line.toLowerCase().includes("error") ? "error" : line.startsWith("$") ? "command" : ""}`}>
                    <span>{String(index + 1).padStart(3, "0")}</span>
                    <code>{line}</code>
                  </div>
                ))
              ) : (
              <div className="terminal-empty">
                {projectRunning && workflow?.run_source === "cli"
                  ? "检测到终端 CLI 正在运行。这里会显示当前项目的 run.log。"
                  : "暂无 run.log 内容。"}
              </div>
              )}
            </div>
          )}
        </section>
      </div>
      {runMutation.error ? <InlineError message={runMutation.error.message} /> : null}
      {cancelRun.error ? <InlineError message={cancelRun.error.message} /> : null}
    </section>
  );
}

function AssetsPage({
  project,
  initialFile,
  onInitialFileUsed
}: {
  project: string;
  initialFile?: string;
  onInitialFileUsed?: () => void;
}) {
  const [selectedFile, setSelectedFile] = useState<string>("");
  const files = useQuery({ queryKey: ["files", project], queryFn: () => api<{ items: FileNode[] }>(`/projects/${project}/files?include_hidden=true`), enabled: Boolean(project) });
  const content = useQuery({ queryKey: ["file", project, selectedFile], queryFn: () => api<any>(`/projects/${project}/files/content?path=${encodeURIComponent(selectedFile)}`), enabled: Boolean(project && selectedFile) });
  useEffect(() => {
    if (!initialFile) return;
    setSelectedFile(projectRelativePath(project, initialFile));
    onInitialFileUsed?.();
  }, [initialFile, onInitialFileUsed, project]);
  if (!project) return <EmptyState title="未选择项目" />;
  return (
    <section className="page assets-layout">
      <div className="asset-tree panel">
        <h2><FolderTree size={18} /> 文件树</h2>
        <FileTree nodes={files.data?.items || []} onSelect={setSelectedFile} selected={selectedFile} />
      </div>
      <div className="reader panel">
        <h2><ScrollText size={18} /> {selectedFile || "选择文件"}</h2>
        {content.isLoading ? <p>正在读取...</p> : content.data?.kind === "markdown" ? (
          <article className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{content.data.content}</ReactMarkdown></article>
        ) : (
          <pre className="source-view">{content.data?.content || "左侧选择 Markdown、JSON、TXT 或日志文件。"}</pre>
        )}
      </div>
      <aside className="context-panel panel">
        <h2><ListChecks size={18} /> 文件信息</h2>
        {content.data ? (
          <div className="kv-list">
            <span>类型</span><strong>{content.data.kind}</strong>
            <span>大小</span><strong>{content.data.size} bytes</strong>
            <span>更新</span><strong>{formatTime(content.data.updated_at)}</strong>
            <span>只读</span><strong>是</strong>
          </div>
        ) : <p>文件信息会在选择后显示。</p>}
      </aside>
    </section>
  );
}

function FileTree({ nodes, onSelect, selected }: { nodes: FileNode[]; onSelect: (path: string) => void; selected: string }) {
  return (
    <ul className="file-tree">
      {nodes.map((node) => (
        <li key={node.relative_path}>
          <button className={selected === node.relative_path ? "active-file" : ""} onClick={() => !node.is_directory && onSelect(node.relative_path)}>
            {node.is_directory ? <FolderTree size={14} /> : <FileText size={14} />}
            <span>{node.name}</span>
            {node.health !== "ok" ? <i>{node.health}</i> : null}
          </button>
          {node.children ? <FileTree nodes={node.children} onSelect={onSelect} selected={selected} /> : null}
        </li>
      ))}
    </ul>
  );
}

function ChaptersPage({
  project,
  initialFile,
  onInitialFileUsed
}: {
  project: string;
  initialFile?: string;
  onInitialFileUsed?: () => void;
}) {
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const queryClient = useQueryClient();
  const chapters = useQuery({ queryKey: ["chapters", project], queryFn: () => api<any>(`/projects/${project}/chapters`), enabled: Boolean(project) });
  const content = useQuery({ queryKey: ["chapter-content", project, selectedFile], queryFn: () => api<FileContent>(`/projects/${project}/files/content?path=${encodeURIComponent(selectedFile)}`), enabled: Boolean(project && selectedFile) });
  const saveChapter = useMutation({
    mutationFn: () => api<FileContent>(`/projects/${project}/files/content`, {
      method: "PUT",
      body: JSON.stringify({ path: selectedFile, content: draft })
    }),
    onSuccess: () => {
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ["chapter-content", project, selectedFile] });
      queryClient.invalidateQueries({ queryKey: ["chapters", project] });
      queryClient.invalidateQueries({ queryKey: ["files", project] });
    }
  });
  useEffect(() => {
    if (!initialFile || !chapters.data?.items?.length) return;
    const exists = chapters.data.items.some((item: Chapter) => item.relative_path === initialFile);
    if (exists) {
      setSelectedFile(initialFile);
      onInitialFileUsed?.();
    }
  }, [chapters.data?.items, initialFile, onInitialFileUsed]);
  useEffect(() => {
    setIsEditing(false);
    setDraft("");
    saveChapter.reset();
  }, [selectedFile]);
  useEffect(() => {
    if (!isEditing && content.data?.content !== undefined) {
      setDraft(content.data.content);
    }
  }, [content.data?.content, isEditing]);
  const startEditing = () => {
    setDraft(content.data?.content || "");
    setIsEditing(true);
  };
  const cancelEditing = () => {
    setDraft(content.data?.content || "");
    setIsEditing(false);
    saveChapter.reset();
  };
  return (
    <section className="page split-page">
      <div className="panel">
        <h2><BookOpen size={18} /> 章节列表</h2>
        <div className="chapter-stats">
          <Metric label="已生成" value={chapters.data?.generated || 0} />
          <Metric label="总字数" value={chapters.data?.total_words || 0} />
        </div>
        <div className="chapter-list">
          {(chapters.data?.items || []).map((item: Chapter) => (
            <button key={item.relative_path} className={selectedFile === item.relative_path ? "active-file" : ""} onClick={() => setSelectedFile(item.relative_path)}>
              <strong>{item.index}. {item.title}</strong>
              <span>{item.word_count} 字 · {item.health}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="panel reader">
        <div className="reader-title-row">
          <h2><ScrollText size={18} /> 正文阅读</h2>
          {selectedFile ? (
            <div className="reader-actions">
              {isEditing ? (
                <>
                  <button className="secondary-button compact-button" type="button" onClick={cancelEditing} disabled={saveChapter.isPending}>
                    <X size={14} /> 取消
                  </button>
                  <button className="primary-button compact-button" type="button" onClick={() => saveChapter.mutate()} disabled={saveChapter.isPending}>
                    {saveChapter.isPending ? <Loader2 size={14} className="spin" /> : <Save size={14} />} 保存
                  </button>
                </>
              ) : (
                <button className="icon-button" type="button" onClick={startEditing} disabled={content.isLoading} title="编辑正文" aria-label="编辑正文">
                  <Pencil size={17} />
                </button>
              )}
            </div>
          ) : null}
        </div>
        {isEditing ? (
          <textarea className="chapter-editor" value={draft} onChange={(event) => setDraft(event.target.value)} autoFocus spellCheck={false} />
        ) : (
          <article className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.data?.content || "选择章节后阅读正文。"}</ReactMarkdown>
          </article>
        )}
        {saveChapter.error ? <InlineError message={saveChapter.error.message} /> : null}
      </div>
    </section>
  );
}

function ExportPage({ project }: { project: string }) {
  const [formats, setFormats] = useState<string[]>(["md", "txt", "epub"]);
  const check = useQuery({ queryKey: ["export-check", project], queryFn: () => api<any>(`/projects/${project}/export/check`), enabled: Boolean(project) });
  const exportMutation = useMutation({
    mutationFn: () => api<any>(`/projects/${project}/export`, { method: "POST", body: JSON.stringify({ formats }) })
  });
  return (
    <section className="page export-grid">
      <div className="panel">
        <h2><ListChecks size={18} /> 成书检查</h2>
        <div className="check-list">
          {(check.data?.checks || []).map((item: any) => (
            <div key={item.key} className={`check ${item.status}`}>
              {item.status === "passed" ? <CheckCircle2 size={17} /> : item.status === "failed" ? <XCircle size={17} /> : <AlertTriangle size={17} />}
              <strong>{item.label}</strong>
              <span>{item.message}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="panel">
        <h2><Download size={18} /> 导出配置</h2>
        <div className="format-grid">
          {["md", "txt", "epub"].map((fmt) => (
            <label key={fmt} className={formats.includes(fmt) ? "format active" : "format"}>
              <input type="checkbox" checked={formats.includes(fmt)} onChange={(event) => setFormats(event.target.checked ? [...formats, fmt] : formats.filter((item) => item !== fmt))} />
              {fmt.toUpperCase()}
            </label>
          ))}
        </div>
        <button className="primary-button" onClick={() => exportMutation.mutate()} disabled={!formats.length || exportMutation.isPending}>
          {exportMutation.isPending ? <Loader2 className="spin" size={16} /> : <Download size={16} />} 执行导出
        </button>
        {exportMutation.error ? <InlineError message={exportMutation.error.message} /> : null}
        {exportMutation.data ? (
          <div className="receipt">
            {exportMutation.data.data.outputs.map((item: any) => (
              <div key={item.relative_path}><strong>{item.format.toUpperCase()}</strong><span>{item.relative_path}</span></div>
            ))}
          </div>
        ) : null}
      </div>
      <div className="panel">
        <h2><BookOpen size={18} /> 目录预览</h2>
        <div className="chapter-list compact">
          {(check.data?.chapters || []).map((item: Chapter) => (
            <div key={item.relative_path}><strong>{item.index}. {item.title}</strong><span>{item.word_count} 字</span></div>
          ))}
        </div>
      </div>
    </section>
  );
}

function LogsPage({ project }: { project: string }) {
  const [logId, setLogId] = useState("");
  const logs = useQuery({ queryKey: ["logs", project], queryFn: () => api<{ items: LogEntry[] }>(`/projects/${project}/logs`), enabled: Boolean(project), refetchInterval: 5000 });
  const content = useQuery({ queryKey: ["log-content", project, logId], queryFn: () => api<any>(`/projects/${project}/logs/${encodeURIComponent(logId)}?tail=800`), enabled: Boolean(project && logId) });
  return (
    <section className="page split-page">
      <div className="panel">
        <h2><Terminal size={18} /> 历史日志</h2>
        <div className="log-list">
          {(logs.data?.items || []).map((item) => (
            <button key={item.log_id} className={logId === item.log_id ? "active-file" : ""} onClick={() => setLogId(item.log_id)}>
              <strong>{item.log_id}</strong>
              <span>{item.source} · {item.step || "run"} · {formatTime(item.updated_at)}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="panel log-detail">
        <h2><ScrollText size={18} /> 日志详情</h2>
        <pre>{content.data?.content || "选择一条日志查看 tail 内容。"}</pre>
      </div>
    </section>
  );
}

function SettingsPage({ environment }: { environment: any }) {
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<any>("/settings") });
  const items = [
    ["Python", environment?.python?.available, environment?.python?.version],
    ["Requirements", environment?.requirements?.installed, environment?.requirements?.missing?.join(", ") || "installed"],
    ["Claude CLI", environment?.claude?.available, environment?.claude?.version || environment?.claude?.message],
    ["Codex CLI", environment?.codex?.available, environment?.codex?.version || environment?.codex?.message],
    ["Projects", environment?.filesystem?.projects_writable, "projects writable"],
    ["Logs", environment?.filesystem?.logs_writable, "logs writable"]
  ];
  return (
    <section className="page settings-grid">
      <div className="panel">
        <h2><Settings size={18} /> 基础设置</h2>
        <div className="kv-list">
          <span>语言</span><strong>{settings.data?.language}</strong>
          <span>默认后端</span><strong>{settings.data?.provider}</strong>
          <span>工作目录</span><strong>{settings.data?.workspace}</strong>
          <span>配置文件</span><strong>{settings.data?.config_file}</strong>
        </div>
      </div>
      <div className="panel">
        <h2><ListChecks size={18} /> 环境检测</h2>
        <div className="env-list">
          {items.map(([label, ok, message]) => (
            <div key={String(label)} className={ok ? "env ok" : "env fail"}>
              {ok ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}
              <strong>{label}</strong>
              <span>{message || "unknown"}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function EmptyState({ title }: { title: string }) {
  return <section className="page"><div className="empty-state">{title}</div></section>;
}

function InlineError({ message }: { message: string }) {
  return <div className="inline-error"><AlertTriangle size={16} /> {message}</div>;
}

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AppErrorBoundary>
        <App />
      </AppErrorBoundary>
    </QueryClientProvider>
  </React.StrictMode>
);
