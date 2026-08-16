from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

CONFIG = {
 "input_path": "",
 "output_html_path": "",
 "output_markdown_path": "",
 "fallback_title": "",
 "page_title": "",
 "auto_bold_levels": [1, 2],
 "auto_bold_terms": ,
 "plain_text_root_max_children": 10,
 "plain_text_child_max_children": 6,
 "npx_command": "npx",
 "markmap_cli_package": "markmap-cli",
 "markmap_extra_args": [
 "--no-open",
 "--no-toolbar",
 "--offline",
 ],
}

MARKMAP_THEME = {
 "branch_colors": [
 "#F08A5D",
 "#2FBF9B",
 "#8B7CFF",
 "#F2B134",
 "#4D96FF",
 "#E978A1",
 ],
 "leaf_text_colors": [
 "#8A563E",
 "#3E6F60",
 "#5B4B7D",
 "#786229",
 "#486D98",
 "#7E564F",
 ],
 "color_freeze_level": 2,
}

MARKMAP_INIT_OPTIONS = {
 "color": MARKMAP_THEME["branch_colors"],
 "colorFreezeLevel": MARKMAP_THEME["color_freeze_level"],
 "fitRatio": 0.97,
 "maxInitialScale": 1.2,
 "nodeMinHeight": 12,
 "paddingX": 10,
 "spacingHorizontal": 108,
 "spacingVertical": 2,
}

STABLE_THEME_STYLE = """
<style>
:root {
 --mm-bg-1: #f7f7f5;
 --mm-bg-2: #eceeeb;
 --mm-ink-1: #132724;
 --mm-ink-2: #36524d;
 --mm-line: rgba(29, 63, 58, 0.26);
 --mm-node-bg: rgba(255, 251, 245, 0.88);
 --mm-node-border: rgba(19, 39, 36, 0.10);
 --mm-node-shadow: 0 10px 28px rgba(17, 34, 31, 0.08);
 --mm-accent: #b55a3c;
}

html {
 font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
 background:
 radial-gradient(circle at top left, rgba(120, 140, 170, 0.05), transparent 24%),
 radial-gradient(circle at bottom right, rgba(90, 110, 120, 0.05), transparent 28%),
 linear-gradient(135deg, var(--mm-bg-1), var(--mm-bg-2));
}

body {
 background: transparent;
}

body::before {
 content: "";
 position: fixed;
 inset: 14px;
 border: 1px solid rgba(19, 39, 36, 0.08);
 border-radius: 24px;
 pointer-events: none;
}

#mindmap {
 background: transparent;
}

.mm-toolbar {
 border: 1px solid rgba(19, 39, 36, 0.08) !important;
 border-radius: 999px !important;
 background: rgba(255, 251, 245, 0.92) !important;
 box-shadow: 0 12px 32px rgba(17, 34, 31, 0.10) !important;
 backdrop-filter: blur(10px);
}

.mm-toolbar-brand.active,
.mm-toolbar-brand:hover,
.mm-toolbar-item.active,
.mm-toolbar-item:hover {
 background: rgba(212, 222, 217, 0.92) !important;
}

.mm-toolbar-brand > *,
.mm-toolbar-item > * {
 color: #5f716d !important;
}

.mm-branch-rich,
.mm-branch-rich * {
 color: inherit !important;
}

.mm-branch-rich strong,
.mm-branch-rich b {
 font-weight: 800 !important;
}

.mm-branch-rich em,
.mm-branch-rich i {
 font-style: italic !important;
}

.mm-branch-rich code {
 font-family: "Cascadia Code", "Consolas", monospace !important;
}
</style>
"""

STABLE_THEME_SCRIPT = """
<script>
(function  {
 const branchThemes = [
 { fill: "#F08A5D", line: "#E56F3A", text: "#A94E23", leaf: "#A94E23" },
 { fill: "#2FBF9B", line: "#179C7C", text: "#106F59", leaf: "#106F59" },
 { fill: "#8B7CFF", line: "#6A57FF", text: "#4B3CB2", leaf: "#4B3CB2" },
 { fill: "#F2B134", line: "#DE9600", text: "#9F6900", leaf: "#9F6900" },
 { fill: "#4D96FF", line: "#1F78FF", text: "#1458B0", leaf: "#1458B0" },
 { fill: "#E978A1", line: "#D94F83", text: "#A33360", leaf: "#A33360" }
 ];

 function themeFor(index) {
 if (index < 0) {
 return { fill: "#85B2A5", line: "#52907F", text: "#2E5B50", leaf: "#2E5B50" };
 }
 return branchThemes[index % branchThemes.length];
 }

 function getResponsiveLayoutOptions {
 const isLandscape = window.innerWidth >= window.innerHeight * 1.18;
 if (isLandscape) {
 return {
 fitRatio: 0.98,
 maxInitialScale: 1.18,
 nodeMinHeight: 12,
 paddingX: 10,
 spacingHorizontal: 152,
 spacingVertical: 1,
 };
 }
 return {
 fitRatio: 0.96,
 maxInitialScale: 1.12,
 nodeMinHeight: 13,
 paddingX: 9,
 spacingHorizontal: 96,
 spacingVertical: 3,
 };
 }

 async function applyResponsiveLayout(forceFit) {
 if (!window.mm || typeof window.mm.setData !== "function") return false;
 const opts = getResponsiveLayoutOptions;
 const signature = JSON.stringify(opts);
 const needRelayout = signature !== window.__mmResponsiveLayoutSignature;
 if (needRelayout) {
 await window.mm.setData(null, opts);
 window.__mmResponsiveLayoutSignature = signature;
 }
 if (forceFit && typeof window.mm.fit === "function") {
 await window.mm.fit(opts.maxInitialScale || 1.15);
 }
 return needRelayout || !!forceFit;
 }

 function collectBranchOrder(svg) {
 const branchOrder = new Map;
 if (!svg) return branchOrder;
 svg.querySelectorAll("g").forEach((group) => {
 const dataNode = group.__data__;
 if (!dataNode || dataNode.depth !== 1) return;
 const key = String((dataNode.state && dataNode.state.path) || (dataNode.data && dataNode.data.content) || "").trim;
 if (!key) return;
 if (!branchOrder.has(key)) {
 branchOrder.set(key, branchOrder.size);
 }
 });
 return branchOrder;
 }

 function getNodeDepth(group) {
 const dataNode = group && group.__data__;
 if (dataNode && typeof dataNode.depth === "number") {
 return dataNode.depth + 1;
 }
 return 3;
 }

 function getOwnForeignObject(group) {
 if (!group || !group.children) return null;
 for (const child of group.children) {
 if ((child.localName || "").toLowerCase === "foreignobject") return child;
 }
 return null;
 }

 function getOwnChildByTag(group, tagName) {
 if (!group || !group.children) return null;
 const target = String(tagName || "").toLowerCase;
 for (const child of group.children) {
 if ((child.localName || "").toLowerCase === target) return child;
 }
 return null;
 }

 function getContentDiv(foreignObject) {
 if (!foreignObject) return null;
 const outer = foreignObject.firstElementChild;
 if (!outer) return null;
 return outer.querySelector(":scope > div[data-tag], :scope > div, [data-tag]") || outer;
 }

 function getBranchRootNode(group) {
 let node = group && group.__data__;
 if (!node) return null;
 while (node && typeof node.depth === "number" && node.depth > 1) {
 node = node.parent || null;
 }
 if (node && node.depth === 1) return node;
 return null;
 }

 function getBranchIndex(group, branchOrder) {
 const branchRoot = getBranchRootNode(group);
 const key = String((branchRoot && branchRoot.state && branchRoot.state.path) || (branchRoot && branchRoot.data && branchRoot.data.content) || "").trim;
 if (!key) return -1;
 if (branchOrder && branchOrder.has(key)) {
 return branchOrder.get(key);
 }
 return -1;
 }

 function normalizeInlineStyles(content, depth) {
 content.classList.add("mm-branch-rich");
 content.querySelectorAll("*").forEach((child) => {
 child.style.background = "transparent";
 child.style.border = "none";
 child.style.boxShadow = "none";
 child.style.pointerEvents = "none";
 child.style.color = "inherit";
 child.style.fontFamily = "inherit";
 child.style.fontSize = "inherit";
 child.style.lineHeight = "inherit";
 child.style.letterSpacing = "inherit";
 const tagName = (child.tagName || "").toUpperCase;
 if (tagName === "STRONG" || tagName === "B") {
 child.style.fontWeight = depth <= 2 ? "800" : "inherit";
 } else {
 child.style.fontWeight = "inherit";
 }
 if (tagName === "EM" || tagName === "I") {
 child.style.fontStyle = "italic";
 } else {
 child.style.fontStyle = "inherit";
 }
 });
 }

 function applyGroupLineStyle(group, depth, theme) {
 if (!group) return;
 const circle = getOwnChildByTag(group, "circle");
 const path = getOwnChildByTag(group, "path");
 const line = getOwnChildByTag(group, "line");

 if (circle) {
 circle.style.strokeLinecap = "round";
 if (depth === 1) {
 circle.style.fill = "#173833";
 circle.style.stroke = "#f7f2ea";
 circle.style.strokeWidth = "2.4";
 circle.setAttribute("r", "7");
 } else if (depth === 2) {
 circle.style.fill = "#f7f2ea";
 circle.style.stroke = theme.fill;
 circle.style.strokeWidth = "3.2";
 circle.setAttribute("r", "5.6");
 } else if (depth === 3) {
 circle.style.fill = "#ffffff";
 circle.style.stroke = theme.line;
 circle.style.strokeWidth = "2.6";
 circle.setAttribute("r", "4.9");
 } else {
 circle.style.fill = "#ffffff";
 circle.style.stroke = theme.line;
 circle.style.strokeWidth = "1.8";
 circle.setAttribute("r", "4.2");
 }
 }

 if (path) {
 path.style.fill = "none";
 path.style.strokeLinecap = "round";
 path.style.strokeLinejoin = "round";
 if (depth === 1) {
 path.style.stroke = "rgba(23, 56, 51, 0.72)";
 path.style.strokeWidth = "3.4";
 } else if (depth === 2) {
 path.style.stroke = theme.fill;
 path.style.strokeWidth = "3";
 } else if (depth === 3) {
 path.style.stroke = theme.line;
 path.style.strokeWidth = "2.4";
 } else {
 path.style.stroke = theme.line;
 path.style.strokeWidth = "1.9";
 }
 path.style.opacity = "1";
 }

 if (line) {
 line.style.strokeLinecap = "round";
 if (depth === 1) {
 line.style.stroke = "rgba(23, 56, 51, 0.56)";
 line.style.strokeWidth = "2.4";
 } else if (depth === 2) {
 line.style.stroke = theme.fill;
 line.style.strokeWidth = "2.2";
 } else {
 line.style.stroke = theme.line;
 line.style.strokeWidth = "1.7";
 }
 }
 }

 function styleContentBlock(content, depth, theme) {
 content.style.display = "inline-block";
 content.style.margin = "0";
 content.style.boxSizing = "border-box";
 content.style.overflow = "visible";
 content.style.whiteSpace = "nowrap";
 content.style.pointerEvents = "none";
 content.style.backdropFilter = "none";
 content.style.textShadow = "none";

 if (depth === 1) {
 content.style.background = "linear-gradient(135deg, #163732 0%, #22443f 100%)";
 content.style.border = "1px solid rgba(255,255,255,0.14)";
 content.style.boxShadow = "0 16px 34px rgba(16, 33, 31, 0.18)";
 content.style.padding = "8px 18px";
 content.style.borderRadius = "18px";
 content.style.color = "#FFF8F0";
 content.style.fontSize = "30px";
 content.style.fontWeight = "800";
 content.style.letterSpacing = "-0.02em";
 content.style.textShadow = "0 1px 0 rgba(255,255,255,0.08)";
 } else if (depth === 2) {
 content.style.background = theme.fill;
 content.style.border = "1px solid " + theme.line;
 content.style.boxShadow = "0 10px 22px rgba(17, 34, 31, 0.08)";
 content.style.padding = "6px 14px";
 content.style.borderRadius = "14px";
 content.style.color = "#fffdf8";
 content.style.fontSize = "21px";
 content.style.fontWeight = "800";
 content.style.letterSpacing = "-0.01em";
 } else if (depth === 3) {
 content.style.background = "transparent";
 content.style.border = "none";
 content.style.boxShadow = "none";
 content.style.padding = "0";
 content.style.borderRadius = "0";
 content.style.color = theme.text;
 content.style.fontSize = "18px";
 content.style.fontWeight = "400";
 content.style.letterSpacing = "0";
 } else {
 content.style.background = "transparent";
 content.style.border = "none";
 content.style.boxShadow = "none";
 content.style.padding = "0";
 content.style.borderRadius = "0";
 content.style.color = theme.leaf;
 content.style.fontSize = "15px";
 content.style.fontWeight = "400";
 content.style.letterSpacing = "0";
 }
 }

 function applyTheme {
 const svg = document.getElementById("mindmap");
 if (!svg) return false;
 const branchOrder = collectBranchOrder(svg);

 const nodeDivs = ;
 svg.querySelectorAll("foreignObject").forEach((foreignObject) => {
 foreignObject.style.overflow = "visible";
 foreignObject.style.pointerEvents = "none";
 const outer = foreignObject.firstElementChild;
 const content = getContentDiv(foreignObject);
 if (!outer || !content) return;

 const group = foreignObject.closest("g");
 const depth = group ? getNodeDepth(group) : 3;
 const branchIndex = group ? getBranchIndex(group, branchOrder) : -1;
 const theme = themeFor(branchIndex);

 applyGroupLineStyle(group, depth, theme);

 outer.style.background = "transparent";
 outer.style.border = "none";
 outer.style.boxShadow = "none";
 outer.style.padding = "0";
 outer.style.margin = "0";
 outer.style.overflow = "visible";
 outer.style.pointerEvents = "none";

 styleContentBlock(content, depth, theme);
 normalizeInlineStyles(content, depth);

 const width = Math.ceil(content.scrollWidth || content.getBoundingClientRect.width || 0) + (depth <= 2 ? 8 : 2);
 const height = Math.ceil(content.scrollHeight || content.getBoundingClientRect.height || 0) + (depth <= 2 ? 6 : 2);
 if (width > 0) {
 foreignObject.setAttribute("width", String(width));
 foreignObject.style.width = width + "px";
 }
 if (height > 0) {
 foreignObject.setAttribute("height", String(height));
 foreignObject.style.height = height + "px";
 }

 if (branchIndex >= 0) {
 const branchRoot = getBranchRootNode(group);
 content.dataset.branchKey = String((branchRoot && branchRoot.state && branchRoot.state.path) || (branchRoot && branchRoot.data && branchRoot.data.content) || "");
 content.dataset.branchIndex = String(branchIndex);
 }

 nodeDivs.push(content);
 });

 return nodeDivs.length > 0;
 }

 let rafId = 0;
 function scheduleApplyTheme {
 if (rafId) cancelAnimationFrame(rafId);
 rafId = requestAnimationFrame( => {
 applyTheme;
 rafId = 0;
 });
 }

 const observer = new MutationObserver( => {
 scheduleApplyTheme;
 });

 let resizeTimer = 0;
 function scheduleResponsiveLayout(forceFit) {
 if (resizeTimer) clearTimeout(resizeTimer);
 resizeTimer = window.setTimeout(async  => {
 const changed = await applyResponsiveLayout(forceFit);
 if (changed) {
 scheduleApplyTheme;
 setTimeout(scheduleApplyTheme, 160);
 setTimeout(scheduleApplyTheme, 420);
 }
 resizeTimer = 0;
 }, 120);
 }

 observer.observe(document.body, { childList: true, subtree: true });
 window.addEventListener("load",  => {
 scheduleResponsiveLayout(true);
 setTimeout(scheduleApplyTheme, 120);
 setTimeout(scheduleApplyTheme, 600);
 setTimeout(scheduleApplyTheme, 1200);
 setTimeout(scheduleApplyTheme, 2200);
 });

 window.addEventListener("resize",  => {
 scheduleResponsiveLayout(true);
 });

 document.addEventListener("click",  => {
 setTimeout(scheduleApplyTheme, 60);
 setTimeout(scheduleApplyTheme, 240);
 setTimeout(scheduleApplyTheme, 600);
 setTimeout(scheduleApplyTheme, 1200);
 });
});
</script>
"""

@dataclass
class MindMapNode:
 text: str
 children: list["MindMapNode"] = field(default_factory=list)

def resolve_path(value: str, *, base_dir: Path) -> Path:
 path = Path(value)
 if path.is_absolute:
 return path
 return (base_dir / path).resolve

def load_text(path: Path) -> str:
 return path.read_text(encoding="utf-8")

def normalize_lines(text: str) -> list[str]:
 return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

def clean_node_text(text: str) -> str:
 collapsed = re.sub(r"\s+", " ", text).strip
 return collapsed or ""

def strip_bold_markup(text: str) -> str:
 without_html = re.sub(r"</?(strong|b)\b[^>]*>", "", text, flags=re.IGNORECASE)
 without_markdown = re.sub(r"(\*\*|__)(.+?)\1", r"\2", without_html)
 return clean_node_text(without_markdown)

def normalize_auto_bold_levels(value: object) -> set[int]:
 if isinstance(value, (list, tuple, set)):
 candidates = value
 elif value in (None, ""):
 candidates = [1, 2]
 else:
 candidates = [value]

 levels: set[int] = set
 for item in candidates:
 try:
 level = int(item)
 except (TypeError, ValueError):
 continue
 if 1 <= level <= 6:
 levels.add(level)

 return levels or {1, 2}

def should_bold_heading_level(heading_level: int) -> bool:
 return heading_level in normalize_auto_bold_levels(CONFIG.get("auto_bold_levels"))

def format_node_text_for_output(text: str, heading_level: int) -> str:
 plain_text = strip_bold_markup(clean_node_text(text))
 if should_bold_heading_level(heading_level):
 return f"**{plain_text}**"
 return plain_text

def build_tree_from_json(path: Path, fallback_title: str) -> MindMapNode:
 data = json.loads(load_text(path))
 return parse_json_node(data, fallback_title)

def parse_json_node(data: object, fallback_title: str) -> MindMapNode:
 if not isinstance(data, dict):
 raise ValueError("JSON mustis， text children。")

 text = clean_node_text(str(data.get("text") or fallback_title))
 raw_children = data.get("children") or 
 if not isinstance(raw_children, list):
 raise ValueError("JSON children mustis。")

 return MindMapNode(
 text=text,
 children=[parse_json_node(item, "") for item in raw_children],
 )

def build_tree_from_markdown(text: str, fallback_title: str) -> MindMapNode:
 root = MindMapNode(text=fallback_title)
 stack: list[tuple[int, MindMapNode]] = [(1, root)]

 for raw_line in normalize_lines(text):
 line = raw_line.strip
 match = re.match(r"^(#{1,6})\s+(.+)$", line)
 if not match:
 continue

 level = len(match.group(1))
 label = clean_node_text(match.group(2))

 if level == 1 and not root.children and root.text == fallback_title:
 root.text = label
 continue

 node = MindMapNode(text=label)
 while stack and stack[-1][0] >= level:
 stack.pop
 parent = stack[-1][1] if stack else root
 parent.children.append(node)
 stack.append((level, node))

 if root.children or root.text != fallback_title:
 return root

 return build_tree_from_bullets(text, fallback_title)

def build_tree_from_bullets(text: str, fallback_title: str) -> MindMapNode:
 root = MindMapNode(text=fallback_title)
 stack: list[tuple[int, MindMapNode]] = [(0, root)]

 for raw_line in normalize_lines(text):
 if not raw_line.strip:
 continue
 match = re.match(r"^(\s*)[-*+]\s+(.+)$", raw_line)
 if not match:
 continue

 indent = len(match.group(1).replace("\t", " "))
 level = indent // 2 + 1
 label = clean_node_text(match.group(2))
 node = MindMapNode(text=label)

 while stack and stack[-1][0] >= level:
 stack.pop
 parent = stack[-1][1] if stack else root
 parent.children.append(node)
 stack.append((level, node))

 if not root.children:
 return build_tree_from_plain_text(text, fallback_title)

 return root

def deduplicate_texts(items: list[str]) -> list[str]:
 result: list[str] = 
 seen: set[str] = set
 for item in items:
 cleaned = clean_node_text(item)
 if not cleaned or cleaned in seen:
 continue
 seen.add(cleaned)
 result.append(cleaned)
 return result

def split_plain_text_blocks(text: str) -> list[str]:
 paragraph_blocks = [
 clean_node_text(block)
 for block in re.split(r"\n\s*\n+", text)
 if block.strip
 ]
 if len(paragraph_blocks) > 1:
 return deduplicate_texts(paragraph_blocks)

 lines = [clean_node_text(line) for line in normalize_lines(text) if line.strip]
 if len(lines) > 1:
 return deduplicate_texts(lines)

 sentences = [
 clean_node_text(item)
 for item in re.split(r"[。！？!?]\s*", text)
 if item.strip
 ]
 return deduplicate_texts(sentences)

def split_plain_text_children(text: str, max_children: int) -> list[str]:
 parts = [
 clean_node_text(item)
 for item in re.split(r"[；;。！？!?]\s*|[、，,]\s*", text)
 if item.strip
 ]
 return deduplicate_texts(parts)[:max_children]

def parse_plain_text_block(block: str, max_children: int) -> MindMapNode:
 normalized_block = clean_node_text(block)
 if not normalized_block:
 return MindMapNode(text="")

 colon_match = re.match(r"^(.{2,20}?)[：:]\s*(.+)$", normalized_block)
 if colon_match:
 title = clean_node_text(colon_match.group(1))
 children = [
 MindMapNode(text=item)
 for item in split_plain_text_children(colon_match.group(2), max_children)
 if item != title
 ]
 if children:
 return MindMapNode(text=title, children=children)

 clauses = split_plain_text_children(normalized_block, max_children + 1)
 if len(clauses) >= 2 and len(clauses[0]) <= 18:
 title = clauses[0]
 children = [MindMapNode(text=item) for item in clauses[1:max_children + 1] if item != title]
 if children:
 return MindMapNode(text=title, children=children)

 return MindMapNode(text=normalized_block)

def detect_plain_text_root_title(lines: list[str], fallback_title: str) -> tuple[str, list[str]]:
 if len(lines) >= 2 and len(lines[0]) <= 20 and not re.search(r"[。！？!?；;，,、：:]", lines[0]):
 return lines[0], lines[1:]
 return fallback_title, lines

def build_tree_from_plain_text(text: str, fallback_title: str) -> MindMapNode:
 lines = [clean_node_text(line) for line in normalize_lines(text) if line.strip]
 if not lines:
 raise ValueError("InputContent，Generate。")

 root_text, content_lines = detect_plain_text_root_title(lines, fallback_title)
 content_text = "\n".join(content_lines).strip if content_lines else text.strip
 blocks = split_plain_text_blocks(content_text)
 if not blocks:
 blocks = content_lines or lines

 max_root_children = int(CONFIG.get("plain_text_root_max_children", 10) or 10)
 max_child_children = int(CONFIG.get("plain_text_child_max_children", 6) or 6)

 children = [
 parse_plain_text_block(block, max_child_children)
 for block in blocks[:max_root_children]
 ]
 return MindMapNode(text=root_text, children=children)

def load_tree(input_path: Path, fallback_title: str) -> MindMapNode:
 if input_path.suffix.lower == ".json":
 return build_tree_from_json(input_path, fallback_title)
 return build_tree_from_markdown(load_text(input_path), fallback_title)

def tree_to_markdown_lines(node: MindMapNode, depth: int = 0) -> list[str]:
 level = max(1, min(depth + 1, 6))
 lines = [f"{'#' * level} {format_node_text_for_output(node.text, level)}"]
 for child in node.children:
 lines.append("")
 lines.extend(tree_to_markdown_lines(child, depth + 1))
 return lines

def write_markdown_source(root: MindMapNode, output_path: Path) -> None:
 output_path.parent.mkdir(parents=True, exist_ok=True)
 output_path.write_text("\n".join(tree_to_markdown_lines(root)) + "\n", encoding="utf-8")

def ensure_npx_available(command: str) -> str:
 executable = shutil.which(command)
 if not executable:
 raise FileNotFoundError(" npx。please Node.js， npx 。")
 return executable

def replace_once(text: str, pattern: str, replacement: str, description: str) -> str:
 updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
 if count != 1:
 raise ValueError(f" {description}。 markmap-cli Output。")
 return updated

def inject_markmap_options(html_text: str) -> str:
 init_options_json = json.dumps(MARKMAP_INIT_OPTIONS, ensure_ascii=False)
 replacement = (
 "})( => window.markmap,"
 "(options) => window.markmap.deriveOptions(Object.assign({}, options || {}, "
 + init_options_json
 + ")),"
 )
 return replace_once(
 html_text,
 r"\}\)\(\(\)\s*=>\s*window\.markmap\s*,\s*null\s*,",
 replacement,
 "markmap Parameters",
 )

def inject_theme_assets(html_text: str) -> str:
 html_text = replace_once(html_text, r"</head>", STABLE_THEME_STYLE + "\n</head>", "head End")
 html_text = replace_once(html_text, r"</body>", STABLE_THEME_SCRIPT + "\n</body>", "body End")
 return html_text

def inject_interactive_features(html_text: str) -> str:
 """："""
 features_js = """
<style>
.toolbar-ext {
 position: fixed; top: 16px; right: 16px; z-index: 999;
 display: flex; gap: 8px; align-items: center;
 background: rgba(255,251,245,0.92); padding: 8px 12px;
 border-radius: 999px; box-shadow: 0 12px 32px rgba(17,34,31,0.10);
 backdrop-filter: blur(10px);
}
.toolbar-ext button {
 border: none; background: transparent; cursor: pointer;
 padding: 6px 12px; border-radius: 20px; font-size: 13px;
 color: #444; transition: all 0.15s; white-space: nowrap;
}
.toolbar-ext button:hover { background: rgba(77,150,255,0.12); color: #1F78FF; }
</style>
<div class="toolbar-ext">
 <button onclick="toggleFullscreen">⛶ </button>
</div>
<script>
function toggleFullscreen {
 if (!document.fullscreenElement) { document.documentElement.requestFullscreen; }
 else { document.exitFullscreen; }
}
</script>"""
 return html_text.replace('</body>', features_js + '\n</body>')

def render_markmap_html(source_markdown: Path, output_html: Path, page_title: str) -> None:
 npx = ensure_npx_available(str(CONFIG["npx_command"]))
 output_html.parent.mkdir(parents=True, exist_ok=True)

 command = [
 npx,
 "--yes",
 str(CONFIG["markmap_cli_package"]),
 *[str(item) for item in CONFIG["markmap_extra_args"]],
 "-o",
 str(output_html),
 str(source_markdown),
 ]
 subprocess.run(command, check=True)

 html_text = output_html.read_text(encoding="utf-8")
 html_text = replace_once(
 html_text,
 r"<title>.*?</title>",
 f"<title>{page_title}</title>",
 "PageTitle",
 )
 html_text = inject_markmap_options(html_text)
 html_text = inject_theme_assets(html_text)
 html_text = inject_interactive_features(html_text)
 output_html.write_text(html_text, encoding="utf-8")

def build_default_output_paths(input_path: Path) -> tuple[Path, Path]:
 stem = input_path.stem
 return (
 (input_path.parent / f"{stem}.html").resolve,
 (input_path.parent / f"{stem}.mindmap.md").resolve,
 )

def describe_tree(node: MindMapNode) -> str:
 child_count = len(node.children)
 preview = ", ".join(child.text for child in node.children[:4]) or ""
 return textwrap.dedent(
 f"""\
 : {node.text}
 : {child_count}
 : {preview}
 """
 ).strip

def main -> None:
 if hasattr(sys.stdout, "reconfigure"):
 sys.stdout.reconfigure(encoding="utf-8")
 if hasattr(sys.stderr, "reconfigure"):
 sys.stderr.reconfigure(encoding="utf-8")

 script_dir = Path(__file__).resolve.parent
 cli_args = sys.argv[1:]

 input_value = cli_args[0].strip if len(cli_args) >= 1 else str(CONFIG["input_path"]).strip
 if not input_value:
 raise ValueError("please CONFIG['input_path'] Input。")

 input_path = resolve_path(input_value, base_dir=script_dir)
 if not input_path.exists:
 raise FileNotFoundError(f"Input：{input_path}")

 output_html_value = cli_args[1].strip if len(cli_args) >= 2 else str(CONFIG["output_html_path"]).strip
 output_markdown_value = cli_args[2].strip if len(cli_args) >= 3 else str(CONFIG["output_markdown_path"]).strip

 if output_html_value and output_markdown_value:
 output_html_path = resolve_path(output_html_value, base_dir=script_dir)
 output_markdown_path = resolve_path(output_markdown_value, base_dir=script_dir)
 else:
 output_html_path, output_markdown_path = build_default_output_paths(input_path)

 root = load_tree(input_path, str(CONFIG["fallback_title"]).strip or "")
 write_markdown_source(root, output_markdown_path)
 render_markmap_html(output_markdown_path, output_html_path, str(CONFIG["page_title"]).strip or root.text)

 print(describe_tree(root))
 print(f"Markdown ：{output_markdown_path}")
 print(f"HTML Output：{output_html_path}")

if __name__ == "__main__":
 main
