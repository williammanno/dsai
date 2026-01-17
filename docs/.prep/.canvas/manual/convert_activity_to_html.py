#!/usr/bin/env python3
"""
Convert ACTIVITY markdown files to Canvas-compatible HTML with card styling.

Usage:
    python convert_activity_to_html.py <input.md> [output.html] [--github-repo URL]
"""

import re
import sys
from pathlib import Path
from typing import Optional


def extract_title(markdown_content: str) -> str:
    """Extract the main title from markdown (first # header after # 📌 ACTIVITY)."""
    lines = markdown_content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('# 📌 ACTIVITY'):
            # Look for the next ## header as the title
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith('## '):
                    title = lines[j].strip()[3:].strip()
                    # Remove emojis for cleaner title
                    title = re.sub(r'[📌✅📤🔧🧱🕒]', '', title).strip()
                    return title
    return "ACTIVITY"


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown text to HTML, preserving formatting."""
    html = markdown_text
    
    # First, extract and protect code blocks
    code_blocks = []
    def replace_code_block(match):
        lang = match.group(1) or ''
        code = match.group(2).strip()
        # Escape HTML in code
        code_escaped = escape_html(code)
        block_id = f"__CODE_BLOCK_{len(code_blocks)}__"
        code_blocks.append(f'<pre style="background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px; overflow-x: auto; margin: 16px 0; white-space: pre-wrap; font-family: monospace; font-size: 14px;"><code>{code_escaped}</code></pre>')
        return block_id
    
    # Match code blocks (\ncode\n```)
    html = re.sub(r'```(\w+)?\s*\n(.*?)```', replace_code_block, html, flags=re.DOTALL)

    
    # Headers (but not inside code blocks)
    html = re.sub(r'^### (.*)$', r'<h3 style="font-size: 18px; font-weight: 600; color: #2d3748; margin: 16px 0 8px 0;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*)$', r'<h2 style="font-size: 22px; font-weight: 600; color: #1a202c; margin: 20px 0 12px 0;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*)$', r'<h1 style="font-size: 28px; font-weight: 700; color: #1a202c; margin: 24px 0 16px 0;">\1</h1>', html, flags=re.MULTILINE)
    
    # Bold (but not inside code)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #2d3748; font-weight: 600;">\1</strong>', html)
    
    # Italics (but not inside code)
    html = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', html)
    
    # Inline code (but not code blocks)
    html = re.sub(r'(?<!`)`([^`\n]+)`(?!`)', r'<code style="background: #f1f5f9; padding: 2px 6px; border-radius: 3px; font-family: monospace; font-size: 0.9em; color: #e11d48;">\1</code>', html)
    
    # Restore code blocks
    for i, block in enumerate(code_blocks):
        html = html.replace(f'__CODE_BLOCK_{i}__', block)
    
    # Links [text](url) - Cornell red
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #B31B1B; text-decoration: none;">\1</a>', html)
    
    # Unordered lists
    lines = html.split('\n')
    in_list = False
    result = []
    for line in lines:
        if re.match(r'^[-*] ', line):
            if not in_list:
                result.append('<ul style="margin: 12px 0; padding-left: 24px; color: #4a5568; line-height: 1.8;">')
                in_list = True
            content = re.sub(r'^[-*] ', '', line)
            # Handle checklist items
            if content.strip().startswith('[ ]'):
                content = re.sub(r'\[ \]', '<span style="color: #94a3b8;">☐</span>', content)
            elif content.strip().startswith('[x]') or content.strip().startswith('[X]'):
                content = re.sub(r'\[[xX]\]', '<span style="color: #10b981;">☑</span>', content)
            result.append(f'<li style="margin: 6px 0;">{content}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(line)
    if in_list:
        result.append('</ul>')
    html = '\n'.join(result)
    
    # Ordered lists
    html = re.sub(r'^(\d+)\. (.*)$', r'<ol style="margin: 12px 0; padding-left: 24px; color: #4a5568; line-height: 1.8;"><li style="margin: 6px 0;">\2</li></ol>', html, flags=re.MULTILINE)
    
    # Remove image references (not useful in Canvas) - do this before horizontal rules
    html = re.sub(r'!\[.*?\]\(.*?\)', '', html)
    
    # Remove "Back to Top" links and variations (with arrows, emojis, etc.)
    html = re.sub(r'←?\s*🏠?\s*\[?Back to Top\]?\([^)]*\)', '', html, flags=re.IGNORECASE)
    html = re.sub(r'←?\s*🏠?\s*Back to Top', '', html, flags=re.IGNORECASE)
    
    # Remove horizontal rules (---, ***, ___) - these are often used as separators before footer
    html = re.sub(r'^[-*_]{3,}$', '', html, flags=re.MULTILINE)
    
    # Paragraphs (lines that aren't already HTML tags)
    lines = html.split('\n')
    result = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('<') and not line.startswith('!['):
            result.append(f'<p style="margin: 12px 0; color: #4a5568; line-height: 1.7;">{line}</p>')
        elif line:
            result.append(line)
    html = '\n'.join(result)
    
    # Clean up empty paragraphs
    html = re.sub(r'<p[^>]*>\s*</p>', '', html)
    
    return html


def extract_sections(markdown_content: str) -> dict:
    """Extract key sections from markdown."""
    sections = {
        'title': extract_title(markdown_content),
        'description': '',
        'tasks': '',
        'submission': '',
        'estimated_time': ''
    }
    
    # Extract estimated time
    time_match = re.search(r'🕒 \*Estimated Time: ([^*]+)\*', markdown_content)
    if time_match:
        sections['estimated_time'] = time_match.group(1).strip()
    
    # Split by major sections
    parts = re.split(r'^## ', markdown_content, flags=re.MULTILINE)
    
    # Find description (text between title and first major section, excluding estimated time)
    if len(parts) > 1:
        # Get text after the first # 📌 ACTIVITY header but before first ## section
        first_section_idx = markdown_content.find('## ')
        if first_section_idx > 0:
            desc_text = markdown_content[:first_section_idx]
            # Remove the # 📌 ACTIVITY line, title, estimated time, and horizontal rules
            desc_lines = []
            for line in desc_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('# 📌') and not line.startswith('🕒') and not line.startswith('---'):
                    # Skip if it's just the title repeated or empty
                    title_lower = sections['title'].lower()
                    line_lower = line.lower()
                    if (line_lower != title_lower and 
                        'activity' not in line_lower and 
                        line and 
                        not line.startswith('#')):
                        desc_lines.append(line)
            if desc_lines:
                # Join and clean up
                desc = '\n'.join(desc_lines).strip()
                # Remove any remaining markdown artifacts
                desc = re.sub(r'^#+\s*', '', desc, flags=re.MULTILINE)
                if desc:
                    sections['description'] = desc
    
    for part in parts:
        if 'Your Task' in part or 'Task' in part:
            sections['tasks'] = part
        elif 'To Submit' in part or 'Submit' in part:
            sections['submission'] = part
    
    return sections


def create_html_card(md_file: Path, github_repo_url: str = "https://github.com/timothyfraser/dsai", 
                     root_path: Optional[Path] = None) -> str:
    """Create HTML card from markdown file."""
    
    # Read markdown
    md_file = md_file.resolve()  # Resolve to absolute path
    content = md_file.read_text(encoding='utf-8')
    
    # Calculate GitHub URL
    # Try to find repo root (go up until we find .git or .gitignore)
    repo_root = None
    current = md_file.parent
    while current != current.parent:
        if (current / '.git').exists() or (current / '.gitignore').exists():
            repo_root = current
            break
        current = current.parent
    
    if repo_root:
        try:
            relative_path = md_file.relative_to(repo_root)
        except ValueError:
            # If not in repo root, use relative to cwd
            relative_path = md_file.relative_to(Path.cwd())
    else:
        # Fallback to relative from current working directory
        relative_path = md_file.relative_to(Path.cwd())
    
    github_url = f"{github_repo_url}/blob/main/{relative_path.as_posix()}"
    
    # Extract sections
    sections = extract_sections(content)
    
    # Determine icon and label based on file type
    icon = "📚"
    label = "ACTIVITY"
    if "ACTIVITY" in md_file.name:
        icon = "📚"
        label = "ACTIVITY"
    elif "LAB" in md_file.name:
        icon = "🔬"
        label = "LAB"
    elif "HOMEWORK" in md_file.name:
        icon = "📝"
        label = "HOMEWORK"
    elif "TOOL" in md_file.name:
        icon = "🛠️"
        label = "TOOL"
    
    # Build HTML
    html_parts = []
    
    # Main card container
    html_parts.append('<div style="margin: 20px auto; max-width: 650px; width: 100%;">')
    html_parts.append('    <div style="background: #ffffff; border: 2px solid #e2e8f0; border-radius: 16px; padding: 40px; margin-bottom: 16px; text-align: center; position: relative;">')
    html_parts.append('        <div style="position: absolute; top: 0; left: 0; right: 0; height: 5px; background: linear-gradient(90deg, #B31B1B 0%, #8B1414 100%); border-radius: 16px 16px 0 0;"></div>')
    html_parts.append(f'        <div style="width: 90px; height: 90px; margin: 0 auto 20px; background: linear-gradient(135deg, #B31B1B 0%, #8B1414 100%); border-radius: 50%; line-height: 90px; font-size: 42px; border: 4px solid rgba(179, 27, 27, 0.2); text-align: center;">{icon}</div>')
    html_parts.append(f'        <p style="font-size: 14px; font-weight: 600; color: #B31B1B; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 1px;">{label}</p>')
    html_parts.append(f'        <h1 style="font-size: 32px; font-weight: 700; color: #1a202c; margin: 0 0 16px 0; padding: 0;">{sections["title"]}</h1>')
    
    # Estimated time
    if sections['estimated_time']:
        html_parts.append(f'        <p style="font-size: 15px; color: #718096; margin: 0 0 24px 0; font-style: italic;">🕒 Estimated Time: {sections["estimated_time"]}</p>')
    
    # Description
    if sections['description']:
        desc_html = markdown_to_html(sections['description'])
        html_parts.append(f'        <div style="text-align: left; margin: 0 0 24px 0;">{desc_html}</div>')
    
    # GitHub button
    html_parts.append(f'        <a href="{github_url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: linear-gradient(135deg, #B31B1B 0%, #8B1414 100%); color: #ffffff; text-decoration: none; padding: 16px 36px; border-radius: 10px; font-size: 17px; font-weight: 600; margin: 12px 0; border: 2px solid rgba(255, 255, 255, 0.25); cursor: pointer;">')
    html_parts.append('            🔗 View Assignment on GitHub for most up to date content')
    html_parts.append('        </a>')
    
    # Tasks section - collapsible
    if sections['tasks']:
        tasks_html = markdown_to_html(sections['tasks'])
        html_parts.append('        <details style="background: #FEF2F2; border-left: 5px solid #B31B1B; border-right: 1px solid #e2e8f0; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; padding: 0; margin-top: 28px; border-radius: 6px; text-align: left;">')
        html_parts.append('            <summary style="cursor: pointer; font-weight: 600; font-size: 18px; color: #B31B1B; padding: 18px 24px; list-style: none;">')
        html_parts.append('                ✅ Your Task')
        html_parts.append('            </summary>')
        html_parts.append('            <div style="padding: 0 24px 18px 24px;">')
        html_parts.append(f'                {tasks_html}')
        html_parts.append('            </div>')
        html_parts.append('        </details>')
    
    # Submission section - collapsible
    if sections['submission']:
        submission_html = markdown_to_html(sections['submission'])
        html_parts.append('        <details style="background: #FEF2F2; border-left: 5px solid #D42D2D; border-right: 1px solid #e2e8f0; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; padding: 0; margin-top: 20px; border-radius: 6px; text-align: left;">')
        html_parts.append('            <summary style="cursor: pointer; font-weight: 600; font-size: 18px; color: #B31B1B; padding: 18px 24px; list-style: none;">')
        html_parts.append('                📤 To Submit')
        html_parts.append('            </summary>')
        html_parts.append('            <div style="padding: 0 24px 18px 24px;">')
        html_parts.append(f'                {submission_html}')
        html_parts.append('            </div>')
        html_parts.append('        </details>')
    
    html_parts.append('    </div>')
    html_parts.append('</div>')
    
    return '\n'.join(html_parts)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python convert_activity_to_html.py <input.md> [output.html] [--github-repo URL]")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    # Parse arguments
    github_repo = "https://github.com/timothyfraser/dsai"
    output_file = None
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--github-repo' and i + 1 < len(sys.argv):
            github_repo = sys.argv[i + 1]
            i += 2
        elif not sys.argv[i].startswith('--'):
            output_file = Path(sys.argv[i])
            i += 1
        else:
            i += 1
    
    if not output_file:
        # Default: output to docs/.prep/.canvas/manual/<foldername>/<filename>.html
        input_file_resolved = input_file.resolve()
        
        # Find repo root
        repo_root = None
        current = input_file_resolved.parent
        while current != current.parent:
            if (current / '.git').exists() or (current / '.gitignore').exists():
                repo_root = current
                break
            current = current.parent
        
        if not repo_root:
            repo_root = Path.cwd()
        
        try:
            rel_path = input_file_resolved.relative_to(repo_root)
        except ValueError:
            rel_path = input_file_resolved.relative_to(Path.cwd())
            repo_root = Path.cwd()
        
        # Extract folder name (parent directory of the file, or 'root' if at root)
        if rel_path.parent.name:
            folder_name = rel_path.parent.name
        else:
            folder_name = 'root'
        
        filename = rel_path.stem + '.html'
        
        # Create output directory
        output_dir = repo_root / 'docs' / '.prep' / '.canvas' / 'manual' / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / filename
    
    # Generate HTML
    html = create_html_card(input_file, github_repo)
    
    # Write output
    output_file.write_text(html, encoding='utf-8')
    
    # Calculate GitHub URL for display
    try:
        repo_root = None
        abs_file = input_file.resolve()
        current = abs_file.parent
        while current != current.parent:
            if (current / '.git').exists() or (current / '.gitignore').exists():
                repo_root = current
                break
            current = current.parent
        if repo_root:
            rel_path = abs_file.relative_to(repo_root)
        else:
            rel_path = abs_file.relative_to(Path.cwd())
    except:
        rel_path = input_file
    
    print(f"Generated: {output_file}")
    print(f"GitHub URL: {github_repo}/blob/main/{rel_path.as_posix()}")


if __name__ == '__main__':
    main()