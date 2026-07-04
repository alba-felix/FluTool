"""SKILL Manager — 统一 AI Agent 技能管理核心层

参考: https://github.com/xingkongliang/skills-manager

核心概念:
- Central Library: 所有已安装技能的中央仓库 (data/skills/)
- Agents/Tools: 不同的 AI 工具 (Claude, Cursor, TRAE 等)，各有自己的技能目录
- Presets: 命名的技能分组，可一键激活/停用到指定 Agent
- Global Workspace: 按 Agent 管理其全局技能目录
- Project Workspace: 项目本地技能集
- Tags: 技能标签，用于分组和过滤
- Sync: 将技能同步到 Agent 目录（symlink 或 copy）
"""

import json
import re
import shutil
import sqlite3
import subprocess
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ── 常量 ────────────────────────────────────────────────────

DEFAULT_SKILLS_ROOT = "data/skills"       # 中央库根目录
DB_FILENAME = "skills.db"                  # SQLite 数据库文件
MARKETPLACE_URL = "https://skills.sh/api/v1/skills"  # skills.sh API

SYNC_MODE_COPY = "copy"
SYNC_MODE_SYMLINK = "symlink"

# 默认 Agent 配置
DEFAULT_AGENTS = [
    {"name": "claude_code",   "display_name": "Claude Code",  "skills_dir": "~/.claude/skills"},
    {"name": "cursor",        "display_name": "Cursor",       "skills_dir": "~/.cursor/skills"},
    {"name": "trae_ide",      "display_name": "TRAE IDE",     "skills_dir": "~/.trae/skills"},
]


# ─ 数据模型 ───────────────────────────────────────────────

class SkillSource(Enum):
    LOCAL = "local"
    GIT = "git"
    ZIP = "zip"
    MARKETPLACE = "marketplace"


@dataclass
class Skill:
    id: str                          # 唯一标识（目录名）
    name: str                        # 显示名称
    description: str = ""            # 描述
    source: str = SkillSource.LOCAL.value  # 来源类型
    git_url: str = ""                # Git 仓库 URL
    git_ref: str = ""                # Git 引用 (branch/tag)
    path: str = ""                   # 本地路径
    tags: List[str] = field(default_factory=list)
    enabled: bool = True             # 是否启用
    installed_at: str = ""           # 安装时间 ISO 格式
    last_updated: str = ""           # 最后更新时间
    upstream_version: str = ""       # 上游版本
    local_version: str = ""          # 本地版本
    file_count: int = 0              # 文件数
    size_kb: float = 0.0             # 大小 KB

    @property
    def has_update(self) -> bool:
        return bool(self.upstream_version and self.local_version
                    and self.upstream_version != self.local_version)


@dataclass
class Agent:
    name: str                        # 内部标识
    display_name: str                # 显示名称
    skills_dir: str                  # 技能目录路径
    enabled: bool = True             # 是否启用
    sync_mode: str = SYNC_MODE_COPY  # 同步模式

    @property
    def expanded_skills_dir(self) -> Path:
        return Path(self.skills_dir).expanduser()


@dataclass
class Preset:
    id: str                          # 唯一标识
    name: str                        # 显示名称
    description: str = ""            # 描述
    skill_ids: List[str] = field(default_factory=list)
    created_at: str = ""


@dataclass
class Workspace:
    id: str
    name: str
    workspace_type: str              # "global" | "project" | "linked"
    agent_name: str = ""             # global 类型关联的 Agent
    project_path: str = ""           # project 类型的项目路径
    linked_path: str = ""            # linked 类型的自定义路径
    active_preset_ids: List[str] = field(default_factory=list)


# ── 数据库层 ───────────────────────────────────────────────

class SkillsDatabase:
    """SQLite 数据库访问层"""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()
        self._seed_defaults()

    def _connect(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def _init_schema(self) -> None:
        c = self._conn
        c.executescript("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                source TEXT DEFAULT 'local',
                git_url TEXT DEFAULT '',
                git_ref TEXT DEFAULT '',
                path TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                enabled INTEGER DEFAULT 1,
                installed_at TEXT DEFAULT '',
                last_updated TEXT DEFAULT '',
                upstream_version TEXT DEFAULT '',
                local_version TEXT DEFAULT '',
                file_count INTEGER DEFAULT 0,
                size_kb REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS agents (
                name TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                skills_dir TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                sync_mode TEXT DEFAULT 'copy'
            );

            CREATE TABLE IF NOT EXISTS presets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS preset_skills (
                preset_id TEXT REFERENCES presets(id) ON DELETE CASCADE,
                skill_id TEXT REFERENCES skills(id) ON DELETE CASCADE,
                PRIMARY KEY (preset_id, skill_id)
            );

            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                workspace_type TEXT NOT NULL,
                agent_name TEXT DEFAULT '',
                project_path TEXT DEFAULT '',
                linked_path TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS workspace_presets (
                workspace_id TEXT REFERENCES workspaces(id) ON DELETE CASCADE,
                preset_id TEXT REFERENCES presets(id) ON DELETE CASCADE,
                PRIMARY KEY (workspace_id, preset_id)
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT DEFAULT ''
            );
        """)
        c.commit()

    def _seed_defaults(self) -> None:
        """插入默认 Agent（如果不存在）"""
        for agent in DEFAULT_AGENTS:
            self._conn.execute(
                "INSERT OR IGNORE INTO agents (name, display_name, skills_dir) VALUES (?, ?, ?)",
                (agent["name"], agent["display_name"], agent["skills_dir"])
            )
        self._conn.commit()

        # 创建默认 Preset
        self._conn.execute(
            "INSERT OR IGNORE INTO presets (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            ("default", "Default", "默认预设", datetime.now().isoformat())
        )
        self._conn.commit()

    # ── Skills CRUD ────────────────────────────────────────

    def insert_skill(self, skill: Skill) -> None:
        self._conn.execute("""
            INSERT OR REPLACE INTO skills
            (id, name, description, source, git_url, git_ref, path, tags,
             enabled, installed_at, last_updated, upstream_version, local_version,
             file_count, size_kb)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill.id, skill.name, skill.description, skill.source,
            skill.git_url, skill.git_ref, skill.path, json.dumps(skill.tags),
            int(skill.enabled), skill.installed_at, skill.last_updated,
            skill.upstream_version, skill.local_version,
            skill.file_count, skill.size_kb
        ))
        self._conn.commit()

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        row = self._conn.execute(
            "SELECT * FROM skills WHERE id = ?", (skill_id,)
        ).fetchone()
        return self._row_to_skill(row) if row else None

    def list_skills(self, tag_filter: Optional[str] = None,
                    source_filter: Optional[str] = None,
                    search_query: Optional[str] = None) -> List[Skill]:
        query = "SELECT * FROM skills WHERE 1=1"
        params: list = []

        if tag_filter:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag_filter}"%')
        if source_filter:
            query += " AND source = ?"
            params.append(source_filter)
        if search_query:
            q = f"%{search_query}%"
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([q, q])

        query += " ORDER BY name"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_skill(r) for r in rows]

    def update_skill_field(self, skill_id: str, **kwargs) -> None:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [skill_id]
        self._conn.execute(f"UPDATE skills SET {sets} WHERE id = ?", vals)
        self._conn.commit()

    def delete_skill(self, skill_id: str) -> None:
        self._conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        self._conn.execute("DELETE FROM preset_skills WHERE skill_id = ?", (skill_id,))
        self._conn.commit()

    # ── Agents ────────────────────────────────────────────

    def list_agents(self) -> List[Agent]:
        rows = self._conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [self._row_to_agent(r) for r in rows]

    def get_agent(self, name: str) -> Optional[Agent]:
        row = self._conn.execute(
            "SELECT * FROM agents WHERE name = ?", (name,)
        ).fetchone()
        return self._row_to_agent(row) if row else None

    def update_agent(self, name: str, **kwargs) -> None:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [name]
        self._conn.execute(f"UPDATE agents SET {sets} WHERE name = ?", vals)
        self._conn.commit()

    # ── Presets ────────────────────────────────────────────

    def list_presets(self) -> List[Preset]:
        rows = self._conn.execute("SELECT * FROM presets ORDER BY name").fetchall()
        result = []
        for r in rows:
            p = self._row_to_preset(r)
            # 加载关联的技能 ID
            skill_rows = self._conn.execute(
                "SELECT skill_id FROM preset_skills WHERE preset_id = ?", (p.id,)
            ).fetchall()
            p.skill_ids = [sr["skill_id"] for sr in skill_rows]
            result.append(p)
        return result

    def create_preset(self, preset: Preset) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO presets (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (preset.id, preset.name, preset.description, preset.created_at)
        )
        # 更新关联
        self._conn.execute("DELETE FROM preset_skills WHERE preset_id = ?", (preset.id,))
        for sid in preset.skill_ids:
            self._conn.execute(
                "INSERT INTO preset_skills (preset_id, skill_id) VALUES (?, ?)",
                (preset.id, sid)
            )
        self._conn.commit()

    def delete_preset(self, preset_id: str) -> None:
        self._conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
        self._conn.execute("DELETE FROM preset_skills WHERE preset_id = ?", (preset_id,))
        self._conn.commit()

    # ── Workspaces ─────────────────────────────────────────

    def list_workspaces(self) -> List[Workspace]:
        rows = self._conn.execute("SELECT * FROM workspaces ORDER BY name").fetchall()
        result = []
        for r in rows:
            w = self._row_to_workspace(r)
            preset_rows = self._conn.execute(
                "SELECT preset_id FROM workspace_presets WHERE workspace_id = ?", (w.id,)
            ).fetchall()
            w.active_preset_ids = [pr["preset_id"] for pr in preset_rows]
            result.append(w)
        return result

    def create_workspace(self, ws: Workspace) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO workspaces (id, name, workspace_type, agent_name, project_path, linked_path) VALUES (?, ?, ?, ?, ?, ?)",
            (ws.id, ws.name, ws.workspace_type, ws.agent_name, ws.project_path, ws.linked_path)
        )
        self._conn.execute("DELETE FROM workspace_presets WHERE workspace_id = ?", (ws.id,))
        for pid in ws.active_preset_ids:
            self._conn.execute(
                "INSERT INTO workspace_presets (workspace_id, preset_id) VALUES (?, ?)",
                (ws.id, pid)
            )
        self._conn.commit()

    def delete_workspace(self, ws_id: str) -> None:
        self._conn.execute("DELETE FROM workspaces WHERE id = ?", (ws_id,))
        self._conn.execute("DELETE FROM workspace_presets WHERE workspace_id = ?", (ws_id,))
        self._conn.commit()

    # ── Activity Log ───────────────────────────────────────

    def log_activity(self, action: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO activity_log (timestamp, action, detail) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), action, detail)
        )
        self._conn.commit()

    def get_recent_activity(self, limit: int = 50) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"timestamp": r["timestamp"], "action": r["action"], "detail": r["detail"]} for r in rows]

    # ── Helpers ────────────────────────────────────────────

    def _row_to_skill(self, row: sqlite3.Row) -> Skill:
        return Skill(
            id=row["id"], name=row["name"], description=row["description"],
            source=row["source"], git_url=row["git_url"], git_ref=row["git_ref"],
            path=row["path"], tags=json.loads(row["tags"]),
            enabled=bool(row["enabled"]), installed_at=row["installed_at"],
            last_updated=row["last_updated"], upstream_version=row["upstream_version"],
            local_version=row["local_version"], file_count=row["file_count"],
            size_kb=row["size_kb"]
        )

    def _row_to_agent(self, row: sqlite3.Row) -> Agent:
        return Agent(
            name=row["name"], display_name=row["display_name"],
            skills_dir=row["skills_dir"], enabled=bool(row["enabled"]),
            sync_mode=row["sync_mode"]
        )

    def _row_to_preset(self, row: sqlite3.Row) -> Preset:
        return Preset(
            id=row["id"], name=row["name"], description=row["description"],
            created_at=row["created_at"]
        )

    def _row_to_workspace(self, row: sqlite3.Row) -> Workspace:
        return Workspace(
            id=row["id"], name=row["name"], workspace_type=row["workspace_type"],
            agent_name=row["agent_name"], project_path=row["project_path"],
            linked_path=row["linked_path"]
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


# ── 业务服务层 ────────────────────────────────────────────

class SkillService:
    """SKILL 管理服务 — 安装、同步、预设、工作区等业务逻辑"""

    def __init__(self, data_root: Path):
        self._data_root = data_root
        self._skills_root = data_root / DEFAULT_SKILLS_ROOT
        self._db = SkillsDatabase(data_root / DB_FILENAME)

    @property
    def db(self) -> SkillsDatabase:
        return self._db

    # ── 安装技能 ──────────────────────────────────────────

    def install_from_local(self, src_path: str, skill_id: Optional[str] = None) -> Skill:
        """从本地目录安装技能"""
        src = Path(src_path).resolve()
        if not src.is_dir():
            raise ValueError(f"Not a directory: {src}")

        sid = skill_id or src.name
        dest = self._skills_root / sid
        if dest.exists():
            raise ValueError(f"Skill '{sid}' already exists at {dest}")

        # 复制文件
        shutil.copytree(src, dest)

        # 解析 SKILL.md
        name, desc = self._parse_skill_md(dest)
        file_count = sum(1 for _ in dest.rglob('*') if _.is_file())
        size_kb = sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()) / 1024

        now = datetime.now().isoformat()
        skill = Skill(
            id=sid, name=name, description=desc,
            source=SkillSource.LOCAL.value, path=str(dest),
            installed_at=now, last_updated=now,
            local_version="local", file_count=file_count,
            size_kb=round(size_kb, 1)
        )
        self._db.insert_skill(skill)
        self._db.log_activity("install", f"Installed local skill '{sid}' from {src}")
        return skill

    def install_from_git(self, url: str, ref: str = "", skill_id: Optional[str] = None) -> Skill:
        """从 Git 仓库安装技能"""
        # 提取 skill_id
        if skill_id is None:
            # git@github.com:user/repo.git → repo
            # https://github.com/user/repo → repo
            m = re.search(r'/([^/]+?)(?:\.git)?$', url)
            skill_id = m.group(1) if m else url.split('/')[-1].replace('.git', '')

        dest = self._skills_root / skill_id
        if dest.exists():
            raise ValueError(f"Skill '{skill_id}' already exists at {dest}")

        # Git clone
        cmd = ["git", "clone", url, str(dest)]
        if ref:
            cmd += ["--branch", ref, "--single-branch"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")

        name, desc = self._parse_skill_md(dest)
        file_count = sum(1 for _ in dest.rglob('*') if _.is_file())
        size_kb = sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()) / 1024

        now = datetime.now().isoformat()
        skill = Skill(
            id=skill_id, name=name, description=desc,
            source=SkillSource.GIT.value, git_url=url, git_ref=ref,
            path=str(dest), installed_at=now, last_updated=now,
            local_version=ref or "HEAD", file_count=file_count,
            size_kb=round(size_kb, 1)
        )
        self._db.insert_skill(skill)
        self._db.log_activity("install", f"Installed git skill '{skill_id}' from {url}")
        return skill

    def install_from_zip(self, zip_path: str, skill_id: Optional[str] = None) -> Skill:
        """从 zip 文件安装技能"""
        zp = Path(zip_path).resolve()
        if not zp.is_file():
            raise ValueError(f"Not a file: {zp}")

        if skill_id is None:
            skill_id = zp.stem

        dest = self._skills_root / skill_id
        if dest.exists():
            raise ValueError(f"Skill '{skill_id}' already exists")

        with zipfile.ZipFile(zp, 'r') as zf:
            zf.extractall(dest)

        name, desc = self._parse_skill_md(dest)
        file_count = sum(1 for _ in dest.rglob('*') if _.is_file())
        size_kb = sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()) / 1024

        now = datetime.now().isoformat()
        skill = Skill(
            id=skill_id, name=name, description=desc,
            source=SkillSource.ZIP.value, path=str(dest),
            installed_at=now, last_updated=now,
            local_version="zip", file_count=file_count,
            size_kb=round(size_kb, 1)
        )
        self._db.insert_skill(skill)
        self._db.log_activity("install", f"Installed zip skill '{skill_id}' from {zp}")
        return skill

    # ── 卸载技能 ──────────────────────────────────────────

    def uninstall_skill(self, skill_id: str) -> None:
        skill = self._db.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")

        # 删除本地文件
        skill_path = Path(skill.path)
        if skill_path.exists():
            shutil.rmtree(skill_path)

        self._db.delete_skill(skill_id)
        self._db.log_activity("uninstall", f"Uninstalled skill '{skill_id}'")

    # ── 同步到 Agent ──────────────────────────────────────

    def sync_to_agent(self, skill_id: str, agent_name: str) -> bool:
        """将技能同步到指定 Agent 目录"""
        skill = self._db.get_skill(skill_id)
        agent = self._db.get_agent(agent_name)
        if not skill or not agent:
            return False

        agent_dir = agent.expanded_skills_dir
        agent_dir.mkdir(parents=True, exist_ok=True)
        dest = agent_dir / skill.id

        # 先移除旧的
        if dest.exists() or dest.is_symlink():
            if dest.is_symlink() or dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()

        if agent.sync_mode == SYNC_MODE_SYMLINK:
            try:
                dest.symlink_to(Path(skill.path).resolve(), target_is_directory=True)
            except OSError:
                # Windows 可能需要管理员权限，降级为 copy
                shutil.copytree(skill.path, dest)
        else:
            shutil.copytree(skill.path, dest)

        self._db.log_activity("sync", f"Synced '{skill_id}' to agent '{agent_name}'")
        return True

    def sync_preset_to_agents(self, preset_id: str, agent_names: List[str]) -> Dict[str, bool]:
        """将预设中的所有技能同步到指定 Agents"""
        preset_list = self._db.list_presets()
        preset = next((p for p in preset_list if p.id == preset_id), None)
        if not preset:
            return {}

        results = {}
        for agent_name in agent_names:
            success = True
            for sid in preset.skill_ids:
                if not self.sync_to_agent(sid, agent_name):
                    success = False
            results[agent_name] = success

        self._db.log_activity("sync_preset", f"Synced preset '{preset_id}' to {agent_names}")
        return results

    # ── 检查更新 ──────────────────────────────────────────

    def check_updates(self, skill_id: Optional[str] = None) -> List[Skill]:
        """检查 Git 技能的上游更新"""
        skills = self._db.list_skills()
        if skill_id:
            skills = [s for s in skills if s.id == skill_id]

        updated = []
        for s in skills:
            if s.source != SkillSource.GIT.value or not s.git_url:
                continue
            try:
                # Git fetch + 比较
                skill_path = Path(s.path)
                result = subprocess.run(
                    ["git", "-C", str(skill_path), "fetch", "origin"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    result = subprocess.run(
                        ["git", "-C", str(skill_path), "rev-parse", "HEAD", "origin/HEAD"],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) >= 2 and lines[0] != lines[1]:
                            s.upstream_version = lines[1][:8]
                            s.local_version = lines[0][:8]
                            updated.append(s)
            except Exception:
                pass

        return updated

    def update_skill(self, skill_id: str) -> bool:
        """更新单个 Git 技能"""
        skill = self._db.get_skill(skill_id)
        if not skill or skill.source != SkillSource.GIT.value:
            return False

        try:
            skill_path = Path(skill.path)
            ref = skill.git_ref or "main"
            subprocess.run(
                ["git", "-C", str(skill_path), "pull", "origin", ref],
                capture_output=True, text=True, timeout=60, check=True
            )
            now = datetime.now().isoformat()
            self._db.update_skill_field(skill_id, last_updated=now)
            self._db.log_activity("update", f"Updated skill '{skill_id}'")
            return True
        except Exception:
            return False

    # ── 标签管理 ──────────────────────────────────────────

    def add_tags(self, skill_id: str, tags: List[str]) -> None:
        skill = self._db.get_skill(skill_id)
        if not skill:
            return
        existing = set(skill.tags)
        existing.update(tags)
        skill.tags = sorted(existing)
        self._db.update_skill_field(skill_id, tags=json.dumps(skill.tags))

    def remove_tag(self, skill_id: str, tag: str) -> None:
        skill = self._db.get_skill(skill_id)
        if not skill:
            return
        skill.tags = [t for t in skill.tags if t != tag]
        self._db.update_skill_field(skill_id, tags=json.dumps(skill.tags))

    def get_all_tags(self) -> List[str]:
        rows = self._db._conn.execute("SELECT tags FROM skills").fetchall()
        all_tags = set()
        for r in rows:
            all_tags.update(json.loads(r["tags"]))
        return sorted(all_tags)

    # ── 辅助方法 ──────────────────────────────────────────

    def _parse_skill_md(self, skill_dir: Path) -> Tuple[str, str]:
        """解析 SKILL.md 或 README.md，返回 (name, description)"""
        for fname in ["SKILL.md", "README.md", "readme.md"]:
            md_file = skill_dir / fname
            if md_file.exists():
                try:
                    content = md_file.read_text(encoding='utf-8', errors='replace')
                except Exception:
                    continue

                # 尝试 frontmatter
                fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if fm_match:
                    fm = {}
                    for line in fm_match.group(1).splitlines():
                        if ':' in line:
                            k, _, v = line.partition(':')
                            fm[k.strip()] = v.strip().strip('"').strip("'")
                    name = fm.get('name', skill_dir.name)
                    desc = fm.get('description', '')
                    if desc:
                        return name, desc

                # 从第一个标题提取名称
                title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
                if title_match:
                    name = title_match.group(1).strip()
                    # 去掉 "SKILL.md - " 前缀
                    name = re.sub(r'^skill\.md\s*[-–:]\s*', '', name, flags=re.IGNORECASE).strip()
                else:
                    name = skill_dir.name

                # 从标题后第一段提取描述
                desc = ""
                lines = content.splitlines()
                past_title = False
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        past_title = True
                        continue
                    if past_title and stripped and not stripped.startswith('---'):
                        desc = stripped[:200]
                        break

                return name, desc

        return skill_dir.name, ""

    def close(self) -> None:
        self._db.close()
