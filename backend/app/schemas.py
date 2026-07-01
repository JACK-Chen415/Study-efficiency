from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict, field_validator

    PYDANTIC_V2 = True
except ImportError:  # pragma: no cover - kept for Pydantic v1 compatibility
    from pydantic import validator

    ConfigDict = None
    PYDANTIC_V2 = False


Location = Literal["dormitory", "library", "classroom", "study_room", "other"]
TaskType = Literal[
    "coursework",
    "exam_review",
    "coding",
    "paper_reading",
    "postgraduate_prep",
    "other",
]
EfficiencyLabel = Literal["low", "medium", "high"]
TimePeriod = Literal["morning", "afternoon", "evening", "late_night"]
DataSource = Literal["real", "demo", "mock", "test"]


class ORMModel(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - exercised only with Pydantic v1
        class Config:
            orm_mode = True


class UserSimpleLoginRequest(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)
    grade: Optional[str] = Field(default=None, max_length=20)
    major: Optional[str] = Field(default=None, max_length=100)

    if PYDANTIC_V2:
        @field_validator("nickname")
        @classmethod
        def strip_nickname(cls, value: str) -> str:
            value = value.strip()
            if not value:
                raise ValueError("nickname is required")
            return value
    else:  # pragma: no cover - exercised only with Pydantic v1
        @validator("nickname")
        def strip_nickname(cls, value: str) -> str:
            value = value.strip()
            if not value:
                raise ValueError("nickname is required")
            return value


class UserResponse(ORMModel):
    id: int
    nickname: str
    grade: Optional[str] = None
    major: Optional[str] = None
    created_at: datetime


class SessionStartRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    start_time: Optional[datetime] = None


class SessionStartResponse(ORMModel):
    id: int
    user_id: int
    start_time: datetime
    status: Literal["in_progress"]


class SessionEndRequest(BaseModel):
    session_id: int = Field(..., gt=0)
    end_time: Optional[datetime] = None
    location: Location
    task_type: TaskType
    goal_clarity: int = Field(..., ge=1, le=5)
    light_level: int = Field(..., ge=1, le=5)
    noise_level: int = Field(..., ge=1, le=5)
    fatigue_level: int = Field(..., ge=1, le=5)
    mood_stress: int = Field(..., ge=1, le=5)
    phone_distraction: int = Field(..., ge=1, le=5)
    efficiency_score: int = Field(..., ge=1, le=5)


class SessionAbandonRequest(BaseModel):
    reason: str = Field(default="user_requested", min_length=1, max_length=100)


class SessionUpdateRequest(BaseModel):
    location: Location
    task_type: TaskType
    goal_clarity: int = Field(..., ge=1, le=5)
    light_level: int = Field(..., ge=1, le=5)
    noise_level: int = Field(..., ge=1, le=5)
    fatigue_level: int = Field(..., ge=1, le=5)
    mood_stress: int = Field(..., ge=1, le=5)
    phone_distraction: int = Field(..., ge=1, le=5)
    efficiency_score: int = Field(..., ge=1, le=5)


class MotionFeatureUploadRequest(BaseModel):
    session_id: int = Field(..., gt=0)
    move_count: Optional[int] = Field(default=None, ge=0)
    shake_count: Optional[int] = Field(default=None, ge=0)
    still_ratio: Optional[float] = Field(default=None, ge=0, le=1)
    avg_acceleration: Optional[float] = Field(default=None, ge=0)
    max_acceleration: Optional[float] = Field(default=None, ge=0)


class MotionFeatureResponse(ORMModel):
    id: int
    session_id: int
    move_count: Optional[int] = None
    shake_count: Optional[int] = None
    still_ratio: Optional[Decimal] = None
    avg_acceleration: Optional[Decimal] = None
    max_acceleration: Optional[Decimal] = None
    created_at: datetime


class PredictionResponse(ORMModel):
    id: int
    session_id: int
    predicted_label: EfficiencyLabel
    confidence: Decimal
    model_version: str
    suggestion: Optional[str] = None
    created_at: datetime


class SessionResponse(ORMModel):
    id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    abandoned_at: Optional[datetime] = None
    abandon_reason: Optional[str] = None
    duration_minutes: Optional[int] = None
    time_period: Optional[TimePeriod] = None
    location: Optional[Location] = None
    task_type: Optional[TaskType] = None
    goal_clarity: Optional[int] = None
    light_level: Optional[int] = None
    noise_level: Optional[int] = None
    fatigue_level: Optional[int] = None
    mood_stress: Optional[int] = None
    phone_distraction: Optional[int] = None
    efficiency_score: Optional[int] = None
    efficiency_label: Optional[EfficiencyLabel] = None
    status: Literal["in_progress", "completed", "abandoned"]


class SessionDetailResponse(SessionResponse):
    motion_features: Optional[MotionFeatureResponse] = None
    latest_prediction: Optional[PredictionResponse] = None


class SessionListResponse(BaseModel):
    items: list[SessionResponse]
    total: int


class SessionDeleteResponse(BaseModel):
    deleted_session_id: int
    archived_id: int
    deleted_at: datetime
    message: str


class ModelTrainRequest(BaseModel):
    model_type: Literal["random_forest_classifier"] = "random_forest_classifier"
    test_size: float = Field(default=0.25, gt=0, lt=1)
    random_state: int = 42
    data_source: DataSource = "real"


class ModelTrainResponse(BaseModel):
    model_version: str
    sample_count: int
    status: Literal["trained"]
    data_source: DataSource
    label_distribution: dict[str, int]
    valid_for_research_conclusion: bool
    warnings: list[str] = []
    metrics: dict
    dummy_baseline: dict


class ModelPredictRequest(BaseModel):
    session_id: int = Field(..., gt=0)


class ModelPredictNextRequest(BaseModel):
    location: Location
    task_type: TaskType
    duration_minutes: int = Field(..., ge=1, le=480)
    goal_clarity: int = Field(..., ge=1, le=5)
    light_level: int = Field(..., ge=1, le=5)
    noise_level: int = Field(..., ge=1, le=5)
    fatigue_level: int = Field(..., ge=1, le=5)
    mood_stress: int = Field(..., ge=1, le=5)
    phone_distraction: int = Field(..., ge=1, le=5)


class FeatureSuggestion(BaseModel):
    field: str
    field_label: str
    current_value: int
    suggested_value: int
    impact: str


class ModelPredictNextResponse(BaseModel):
    predicted_label: EfficiencyLabel
    confidence: float
    suggestion: str
    feature_suggestions: list[FeatureSuggestion]


class ModelMetricsResponse(BaseModel):
    model_version: str
    trained_at: str
    status: str
    data_source: DataSource
    sample_count: int
    label_distribution: dict[str, int]
    valid_for_research_conclusion: bool
    warnings: list[str] = []
    evaluation: Optional[dict] = None
    metrics: Optional[dict] = None
    dummy_baseline: Optional[dict] = None


class FeatureImportanceItem(BaseModel):
    rank: int
    feature_name: str
    importance_score: float


class FeatureImportanceResponse(BaseModel):
    model_version: str
    items: list[FeatureImportanceItem]


class AnalyticsOverviewResponse(BaseModel):
    user_id: int
    total_sessions: int
    total_duration_minutes: int
    avg_duration_minutes: Optional[float] = None
    avg_efficiency_score: Optional[float] = None
    high_efficiency_ratio: float
    label_distribution: dict[str, int]
    motion_available_count: int
    latest_session_at: Optional[datetime] = None
    latest_prediction: Optional[PredictionResponse] = None
    data_scope: str


class AnalyticsTrendItem(BaseModel):
    date: str
    session_count: int
    duration_minutes: int
    avg_duration_minutes: Optional[float] = None
    avg_efficiency_score: Optional[float] = None
    high_efficiency_ratio: float


class AnalyticsTrendResponse(BaseModel):
    user_id: int
    items: list[AnalyticsTrendItem]


class TimePeriodAnalysisItem(BaseModel):
    time_period: TimePeriod
    session_count: int
    duration_minutes: int
    avg_duration_minutes: Optional[float] = None
    avg_efficiency_score: Optional[float] = None
    high_efficiency_ratio: float


class MotionEfficiencyPoint(BaseModel):
    session_id: int
    start_time: datetime
    move_count: int
    shake_count: int
    still_ratio: Optional[float] = None
    efficiency_score: int
    efficiency_label: EfficiencyLabel


class AnalyticsRuleSuggestion(BaseModel):
    code: str
    title: str
    message: str
    trigger_count: int
    active: bool


class AnalyticsModelSnapshot(BaseModel):
    available: bool
    model_version: Optional[str] = None
    data_source: Optional[DataSource] = None
    sample_count: Optional[int] = None
    valid_for_research_conclusion: bool = False
    metrics: Optional[dict] = None
    warnings: list[str] = []
    feature_importance: list[FeatureImportanceItem] = []


class AnalyticsFactorAnalysisResponse(BaseModel):
    user_id: int
    sample_count: int
    time_periods: list[TimePeriodAnalysisItem]
    motion_efficiency_points: list[MotionEfficiencyPoint]
    rule_suggestions: list[AnalyticsRuleSuggestion]
    model_snapshot: AnalyticsModelSnapshot
