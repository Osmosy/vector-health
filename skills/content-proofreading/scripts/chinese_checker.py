#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chinese check module"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

class IssueSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class IssueCategory(Enum):
    TYPO = "typo"
    GRAMMAR = "grammar"
    PUNCTUATION = "punctuation"
    STYLE = "style"
    FORMAT = "format"

@dataclass
class ChineseIssue:
    type: str
    category: IssueCategory
    message: str
    suggestion: Optional[str] = None
    start: int = 0
    end: int = 0
    line: int = 1
    severity: IssueSeverity = IssueSeverity.WARNING

class ChineseChecker:
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.issues = []
        self.common_typos = {
            "teh": "the", "recieve": "receive", "occured": "occurred",
            "definately": "definitely", "seperate": "separate", "occurence": "occurrence",
            "accomodate": "accommodate", "neccessary": "necessary", "succesful": "successful",
            "independant": "independent", "existance": "existence", "perseverence": "perseverance"
        }

    def check(self, text: str) -> List[ChineseIssue]:
        """Perform Chinese text checks"""
        self.issues = []
        lines = text.split(chr(10))
        for line_num, line in enumerate(lines, 1):
            self._check_typos(line, line_num)
            if self.strict:
                self._check_punctuation(line, line_num)
        return self.issues

    def _check_typos(self, line: str, line_num: int):
        for wrong, correct in self.common_typos.items():
            if wrong in line:
                pos = line.find(wrong)
                self.issues.append(ChineseIssue(
                    type="typo", category=IssueCategory.TYPO,
                    message=f"Suspected typo: {wrong}", suggestion=f"Should be: {correct}",
                    start=pos, end=pos + len(wrong), line=line_num,
                    severity=IssueSeverity.ERROR))

    def _check_punctuation(self, line: str, line_num: int):
        """Check for mixed Chinese/English punctuation usage"""
        if re.search(r'[\u4e00-\u9fff][,\.!?:;]', line):
            self.issues.append(ChineseIssue(
                type="punctuation", category=IssueCategory.PUNCTUATION,
                message="English punctuation used in Chinese text",
                suggestion="Use Chinese punctuation (，。！？：；)",
                line=line_num,
                severity=IssueSeverity.WARNING))
