"""
Data models and schemas for Linus: Autonomous Adversarial PR Verifier.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RiskVectorType(str, Enum):
    EMPTY_COLLECTION_INDEXING = "empty_collection_indexing"
    ZERO_DIVISION = "zero_division"
    NULLABLE_ATTRIBUTE_ACCESS = "nullable_attribute_access"
    UNCHECKED_DICT_KEY = "unchecked_dict_key"
    BOUNDARY_INTEGER_OVERFLOW = "boundary_integer_overflow"
    INVERTED_LOGIC = "inverted_logic"


class FunctionParameter(BaseModel):
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None


class FunctionSignature(BaseModel):
    name: str
    line_number: int
    parameters: List[FunctionParameter] = Field(default_factory=list)
    return_type: Optional[str] = None
    risk_vectors: List[RiskVectorType] = Field(default_factory=list)
    docstring: Optional[str] = None


class ASTAnalysisResult(BaseModel):
    file_path: str
    functions: List[FunctionSignature] = Field(default_factory=list)
    imported_symbols: List[str] = Field(default_factory=list)
    total_lines: int = 0
    raw_source: str = ""


class TestStatus(str, Enum):
    __test__ = False
    PASS = "PASS"
    UNCAUGHT_EXCEPTION = "UNCAUGHT_EXCEPTION"
    FAIL_ASSERTION = "FAIL_ASSERTION"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class TestExecutionResult(BaseModel):
    __test__ = False
    status: TestStatus
    exit_code: int
    test_code: str
    stdout: str = ""
    stderr: str = ""
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    exception_line: Optional[int] = None
    stack_trace: str = ""
    duration_ms: float = 0.0


class PatchProposal(BaseModel):
    file_path: str
    original_code: str
    patched_code: str
    diff_patch: str
    explanation: str


class DualVerificationResult(BaseModel):
    verified: bool
    adversarial_test_passed: bool
    baseline_suite_passed: bool
    baseline_tests_count: int = 0
    permanent_test_path: Optional[str] = None
    details: str = ""


class LinusAuditResult(BaseModel):
    pr_id: str
    repository: str
    status: str  # "VERIFIED_DEFECT", "VERIFIED_CLEAN", "ESCALATED"
    defect_proven: bool = False
    ast_summary: Optional[ASTAnalysisResult] = None
    failing_test: Optional[TestExecutionResult] = None
    patch: Optional[PatchProposal] = None
    dual_verification: Optional[DualVerificationResult] = None
    telemetry_trace: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time_seconds: float = 0.0
