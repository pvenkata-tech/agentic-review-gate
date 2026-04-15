"""
Diff parsing utility for extracting changed code from unified diff format.

This module provides efficient parsing of git diffs to extract only the
changed lines, which reduces the amount of code passed to LLMs and agents.
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class DiffHunk:
    """Represents a single hunk of changes in a diff."""
    file_path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]  # Lines in the hunk (including context)
    added_lines: List[Tuple[int, str]]  # (line_number, content) for added lines
    removed_lines: List[Tuple[int, str]]  # (line_number, content) for removed lines


@dataclass
class FileDiff:
    """Represents all changes to a single file."""
    file_path: str
    old_file: str
    new_file: str
    is_binary: bool
    is_renamed: bool
    is_deleted: bool
    is_added: bool
    hunks: List[DiffHunk]


class DiffParser:
    """Parse unified diff format into structured data."""
    
    @staticmethod
    def parse(diff_content: str) -> List[FileDiff]:
        """
        Parse unified diff into file diffs.
        
        Args:
            diff_content: Full diff content (git diff output)
            
        Returns:
            List of FileDiff objects
        """
        from code_reviewer.utils.logger import get_logger
        logger = get_logger()
        
        files = []
        
        # Validate input
        if not diff_content or len(diff_content.strip()) == 0:
            logger.warning("DiffParser.parse(): Received empty diff content")
            return files
        
        # Check if this looks like a valid diff
        if not diff_content.startswith('diff --git') and not diff_content.startswith('==='):
            logger.warning(f"DiffParser.parse(): Diff does not start with 'diff --git'. First 100 chars: {diff_content[:100]}")
            # Still try to parse in case it's a partial diff
        
        lines = diff_content.split('\n')
        logger.debug(f"DiffParser.parse(): Processing {len(lines)} lines from diff")
        
        i = 0
        file_count = 0
        
        while i < len(lines):
            # Look for diff header
            if lines[i].startswith('diff --git'):
                file_diff = DiffParser._parse_file_diff(lines, i)
                if file_diff:
                    files.append(file_diff)
                    file_count += 1
                    logger.debug(f"  File {file_count}: {file_diff.file_path} ({len(file_diff.hunks)} hunks)")
                    # Move index forward by the number of lines consumed
                    i += DiffParser._count_consumed_lines(lines, i)
                else:
                    i += 1
            else:
                i += 1
        
        logger.info(f"DiffParser.parse(): Extracted {file_count} files from diff")
        return files
    
    @staticmethod
    def _parse_file_diff(lines: List[str], start_idx: int) -> FileDiff | None:
        """Parse a single file's diff section."""
        file_path = None
        old_file = None
        new_file = None
        is_binary = False
        is_renamed = False
        is_deleted = False
        is_added = False
        hunks = []
        
        i = start_idx
        
        # Parse the diff header
        diff_line = lines[i]  # "diff --git a/path b/path"
        
        # Extract file paths
        parts = diff_line.split(' ')
        if len(parts) >= 4:
            old_file = parts[2][2:]  # Remove "a/"
            new_file = parts[3][2:]  # Remove "b/"
            file_path = new_file if new_file != '/dev/null' else old_file
        
        i += 1
        
        # Parse metadata lines
        while i < len(lines):
            line = lines[i]
            
            if line.startswith('index '):
                i += 1
                continue
            elif line.startswith('---'):
                i += 1
                continue
            elif line.startswith('+++'):
                i += 1
                continue
            elif line.startswith('Binary files'):
                is_binary = True
                i += 1
                break
            elif line.startswith('rename from'):
                is_renamed = True
                i += 1
                continue
            elif line.startswith('new file mode'):
                is_added = True
                i += 1
                continue
            elif line.startswith('deleted file mode'):
                is_deleted = True
                i += 1
                continue
            elif line.startswith('@@'):
                # Start of hunks
                break
            elif line.startswith('diff --git'):
                # Next file
                break
            else:
                i += 1
        
        # Parse hunks
        while i < len(lines) and lines[i].startswith('@@'):
            hunk = DiffParser._parse_hunk(lines, i)
            if hunk:
                hunks.append(hunk)
            
            # Find next hunk or file
            i += 1
            while i < len(lines):
                if lines[i].startswith('@@'):
                    break
                elif lines[i].startswith('diff --git'):
                    break
                else:
                    i += 1
        
        return FileDiff(
            file_path=file_path,
            old_file=old_file,
            new_file=new_file,
            is_binary=is_binary,
            is_renamed=is_renamed,
            is_deleted=is_deleted,
            is_added=is_added,
            hunks=hunks,
        )
    
    @staticmethod
    def _parse_hunk(lines: List[str], start_idx: int) -> DiffHunk | None:
        """Parse a single hunk (starting with @@...)."""
        hunk_header = lines[start_idx]  # "@@ -old_start,old_count +new_start,new_count @@"
        
        # Parse hunk header: @@ -10,5 +20,7 @@
        try:
            header_part = hunk_header.split('@@')[1].strip()
            ranges = header_part.split(' ')[0]
            old_range, new_range = ranges.split('+')
            
            old_start, old_count = DiffParser._parse_range(old_range)
            new_start, new_count = DiffParser._parse_range(new_range)
        except (IndexError, ValueError):
            return None
        
        # Extract file path from context (if present)
        file_path = None
        if len(hunk_header.split('@@')) > 2:
            file_path = hunk_header.split('@@')[2].strip()
        
        # Parse hunk lines
        hunk_lines = []
        added_lines = []
        removed_lines = []
        
        i = start_idx + 1
        current_new_line = new_start
        current_old_line = old_start
        
        while i < len(lines):
            line = lines[i]
            
            if line.startswith('@@'):
                break
            elif line.startswith('diff --git'):
                break
            elif line.startswith('+'):
                # Added line
                content = line[1:]
                hunk_lines.append(line)
                added_lines.append((current_new_line, content))
                current_new_line += 1
            elif line.startswith('-'):
                # Removed line
                content = line[1:]
                hunk_lines.append(line)
                removed_lines.append((current_old_line, content))
                current_old_line += 1
            elif line.startswith(' '):
                # Context line
                hunk_lines.append(line)
                current_new_line += 1
                current_old_line += 1
            elif line.startswith('\\'):
                # "\ No newline at end of file"
                hunk_lines.append(line)
            else:
                # End of hunk
                break
            
            i += 1
        
        return DiffHunk(
            file_path=file_path or "unknown",
            old_start=old_start,
            old_count=old_count,
            new_start=new_start,
            new_count=new_count,
            lines=hunk_lines,
            added_lines=added_lines,
            removed_lines=removed_lines,
        )
    
    @staticmethod
    def _parse_range(range_str: str) -> Tuple[int, int]:
        """Parse a range string like '-10,5' or '+20,7'."""
        range_str = range_str.lstrip('-+').strip()
        parts = range_str.split(',')
        
        start = int(parts[0])
        count = int(parts[1]) if len(parts) > 1 else 1
        
        return start, count
    
    @staticmethod
    def _count_consumed_lines(lines: List[str], start_idx: int) -> int:
        """Count how many lines are part of this file's diff."""
        count = 1
        i = start_idx + 1
        
        while i < len(lines):
            if lines[i].startswith('diff --git'):
                break
            count += 1
            i += 1
        
        return count


class DiffAnalyzer:
    """Analyze diff to extract relevant information for agents."""
    
    @staticmethod
    def get_changed_files(file_diffs: List[FileDiff]) -> List[str]:
        """Get list of changed file paths."""
        return [f.file_path for f in file_diffs if f.file_path]
    
    @staticmethod
    def get_added_lines(file_diffs: List[FileDiff]) -> Dict[str, List[Tuple[int, str]]]:
        """Get all added lines grouped by file."""
        result = {}
        for file_diff in file_diffs:
            added = []
            for hunk in file_diff.hunks:
                added.extend(hunk.added_lines)
            if added:
                result[file_diff.file_path] = added
        return result
    
    @staticmethod
    def get_removed_lines(file_diffs: List[FileDiff]) -> Dict[str, List[Tuple[int, str]]]:
        """Get all removed lines grouped by file."""
        result = {}
        for file_diff in file_diffs:
            removed = []
            for hunk in file_diff.hunks:
                removed.extend(hunk.removed_lines)
            if removed:
                result[file_diff.file_path] = removed
        return result
    
    @staticmethod
    def get_context_around_line(file_diffs: List[FileDiff], file_path: str, line_num: int, context_lines: int = 3) -> str:
        """Get context lines around a specific line number."""
        for file_diff in file_diffs:
            if file_diff.file_path == file_path:
                for hunk in file_diff.hunks:
                    # Check if line is in this hunk
                    for i, line in enumerate(hunk.lines):
                        if line.startswith('+') and hunk.added_lines:
                            for added_line_num, added_content in hunk.added_lines:
                                if added_line_num == line_num:
                                    # Found the line, get context
                                    start = max(0, i - context_lines)
                                    end = min(len(hunk.lines), i + context_lines + 1)
                                    return '\n'.join(hunk.lines[start:end])
        
        return ""
    
    @staticmethod
    def get_summary_stats(file_diffs: List[FileDiff]) -> Dict[str, int]:
        """Get summary statistics about the diff."""
        total_added = 0
        total_removed = 0
        files_changed = 0
        
        for file_diff in file_diffs:
            files_changed += 1
            for hunk in file_diff.hunks:
                total_added += len(hunk.added_lines)
                total_removed += len(hunk.removed_lines)
        
        return {
            "files_changed": files_changed,
            "total_lines_added": total_added,
            "total_lines_removed": total_removed,
            "total_lines_changed": total_added + total_removed,
        }
