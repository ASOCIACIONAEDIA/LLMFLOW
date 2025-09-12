from enum import Enum

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    CORPORATE_ADMIN = "corporate_admin"
    SUPERADMIN = "superadmin"

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"

class SourceType(str, Enum):
    TRUSTPILOT = "trustpilot"
    GOOGLE = "google"
    TRIPADVISOR = "tripadvisor"
    AMAZON = "amazon"
    DRUNI = "druni"
    MYBUSINESS = "mybusiness"
    PRODUCTS = "products"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobSourceStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class WebSocketEventType(str, Enum):
    """Event types for WebSocket communications"""
    CONNECTED = "connected"
    TASK_STARTED = "task_started"
    PROGRESS = "progress"
    TASK_COMPLETED = "task_completed"
    SOURCE_STARTED = "source_started"  # When a specific source starts (e.g., Trustpilot)
    SOURCE_COMPLETED = "source_completed"  # When a specific source completes
    JOB_COMPLETED = "job_completed"  # When entire job is done
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


    ARCHETYPE_STARTED = "archetype_started"
    ARCHETYPE_FETCHING = "archetype_fetching"
    ARCHETYPE_GENERATING = "archetype_generating"
    ARCHETYPE_SAVING = "archetype_saving"
    ARCHETYPE_COMPLETED = "archetype_completed"
    
    USER_NOTIFICATION = "user_notification"
    SYSTEM_NOTIFICATION = "system_notification"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"
    HEARTBEAT = "heartbeat"

class JobType(str, Enum):
    """High-level job categories that can contain multiple tasks"""
    REVIEW_SCRAPING = "review_scraping"          # Scrape reviews from multiple sources
    SENTIMENT_ANALYSIS = "sentiment_analysis"    # Analyze sentiment of existing reviews
    COMPETITIVE_ANALYSIS = "competitive_analysis" # Compare against competitors
    EXPORT_REPORTS = "export_reports"            # Generate and send reports
    DATA_PROCESSING = "data_processing"          # Clean, normalize, deduplicate data
    NOTIFICATION_BATCH = "notification_batch"    # Send bulk notifications
    BACKUP_RESTORE = "backup_restore"            # System maintenance tasks
    ARCHETYPE_GENERATION = "archetype_generation"
    PRODUCT_DISCOVERY = "product_discovery"

class JobTargetType(str, Enum):
    """Types of entities that jobs can target"""
    ORGANIZATION = "organization"
    COMPETITOR = "competitor"

class ChannelType(str, Enum):
    """Types of channels for WebSocket subscriptions"""
    JOB = "job"
    JOB_PROGRESS = "job_progress"
    JOB_ERRORS = "job_errors"
    USER = "user"
    USER_JOBS = "user_jobs"
    ORG = "org"
    ORG_JOBS = "org_jobs"
    SYSTEM = "system"
    MAINTENANCE = "maintenance"

class WSMessageType(str, Enum):
    """Websocket message types for client-server communication"""
    AUTHENTICATE = "authenticate"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    EVENT = "event"
    HEARTBEAT = "heartbeat"
    CONNECTION_STATUS = "connection_status"
    ERROR = "error"