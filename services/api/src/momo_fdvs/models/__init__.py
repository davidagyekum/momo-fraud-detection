"""Complete P02 persistence model registry.

Importing this package registers every mapped table with SQLAlchemy metadata.
"""

from momo_fdvs.models.analysis import (
    AnalysisRun,
    AnalysisStageRun,
    FraudPrediction,
    FraudRule,
    FraudRuleSet,
    ImageAnalysis,
    ModelVersion,
    RuleEvaluation,
)
from momo_fdvs.models.casework import (
    AuditLog,
    CaseDecision,
    CaseEvent,
    FraudCase,
    IdempotencyRecord,
    Notification,
    ReportArtifact,
)
from momo_fdvs.models.evidence import (
    OCRConfirmation,
    OCRResult,
    Receipt,
    ReceiptDerivative,
    ReceiptTemplate,
    Transaction,
)
from momo_fdvs.models.identity import (
    AdminProfile,
    PasswordResetToken,
    RefreshSession,
    Role,
    User,
    UserRole,
)
from momo_fdvs.models.verification import (
    ReferenceImportBatch,
    ReferenceTransaction,
    VerificationResult,
)

__all__ = [
    "AdminProfile",
    "AnalysisRun",
    "AnalysisStageRun",
    "AuditLog",
    "CaseDecision",
    "CaseEvent",
    "FraudCase",
    "FraudPrediction",
    "FraudRule",
    "FraudRuleSet",
    "IdempotencyRecord",
    "ImageAnalysis",
    "ModelVersion",
    "Notification",
    "OCRConfirmation",
    "OCRResult",
    "PasswordResetToken",
    "Receipt",
    "ReceiptDerivative",
    "ReceiptTemplate",
    "ReferenceImportBatch",
    "ReferenceTransaction",
    "RefreshSession",
    "ReportArtifact",
    "Role",
    "RuleEvaluation",
    "Transaction",
    "User",
    "UserRole",
    "VerificationResult",
]
