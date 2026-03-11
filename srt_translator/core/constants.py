# srt_translator/core/constants.py
MAX_COMPLETION_TOKENS = 120

DEFAULT_GENERATION_MODEL = "gpt-4o-mini"         # model used for DNT / termbase generation
MAX_COMPLETION_TOKENS_DNT = 5000                 # token budget for DNT extraction calls
MAX_COMPLETION_TOKENS_TERMBASE = 5000            # token budget for termbase generation calls
MAX_COMPLETION_TOKENS_DIAGNOSTIC = 160           # token budget for oversize / malformed-JSON probes
MAX_COMPLETION_TOKENS_FALLBACK = 256
MAX_COMPLETION_TOKENS_VALIDATE = 16000
# token budget for single-string plain-text fallback

# Default sampling temperature for generation calls
DEFAULT_TEMPERATURE = 0.75

# Rough heuristic: average characters per token (used for char-budget calculations)
CHARS_PER_TOKEN = 4

# Maximum tokens sent inline to the AI for config generation (~50 K chars)
MAX_INLINE_TOKENS = 12500

# Maximum subtitles sent in a single translation request
MAX_BATCH_SIZE = 8

# Recursive split depth before falling back to single-item retries
MAX_SPLIT_DEPTH = 3

# Per-segment micro-retry attempts before emitting an empty cue
MAX_JSON_RETRIES_PER_SEGMENT = 2

# Circuit-breaker: consecutive decode failures before aborting the run
MAX_CONSECUTIVE_DECODE_FAILURES = 8

# Exponential backoff timing for micro-retries (seconds)
MICRO_BACKOFF_BASE = 0.25
MICRO_BACKOFF_CAP = 1.0

# Minimum token floor so very short cues still get a valid JSON wrapper
STRICT_RETRY_TOKEN_FLOOR = 120

# Token multiplier applied to source-token estimate for the retry cap
STRICT_RETRY_TOKEN_MULTIPLIER = 2.4

# Hard ceiling for strict-retry max_completion_tokens
STRICT_RETRY_TOKEN_CAP = 900

# Frequency penalty applied during strict retries to suppress repetition loops
STRICT_RETRY_FREQUENCY_PENALTY = 0.6

# Minimum translation-to-source token ratio (below = suspiciously short)
MIN_TRANSLATION_TOKEN_RATIO = 0.3

# Maximum translation-to-source token ratio (above = suspiciously long)
MAX_TRANSLATION_TOKEN_RATIO = 2.8

# Oversize heuristic: flag when response tokens ≥ N × prompt tokens
OVERSIZE_RESPONSE_MULTIPLIER = 4

# Character limit for response previews sent to the diagnostic probe
DIAG_RESPONSE_PREVIEW_CHARS = 500

# Maximum source items forwarded to the oversize probe question
DIAG_MAX_SOURCE_ITEMS = 8

# Maximum batch IDs forwarded to the malformed-JSON probe
DIAG_MAX_PROBE_BATCH_IDS = 8

# Minimum acceptable termbase size (triggers a warning if below this)
MIN_TERMBASE_SIZE = 5

# Minimum term count to consider a language TB as a valid soft-band anchor
MIN_ANCHOR_TERM_COUNT = 8

# Minimum translation coverage ratio required before accepting a TB anchor
MIN_ANCHOR_COVERAGE = 0.6

# Top-up oversample factor: ask for (needed + max(2, needed // TOPUP_OVERSAMPLE))
TOPUP_OVERSAMPLE_DIVISOR = 2

# Generic singleton cap: at most this many single-word generic terms per TB
MAX_GENERIC_SINGLETONS = 2

# Minimum distinct-line frequency for a generic singleton to bypass the cap
MIN_GENERIC_SINGLETON_LINE_FREQ = 3

# Termbase chunk size for post-fill translation calls
TERMBASE_FILL_CHUNK_SIZE = 25

# Soft-band floors keyed by approximate transcript token size
SOFT_BAND_FLOOR_SHORT = 6      # ≤ 400 tokens
SOFT_BAND_FLOOR_MEDIUM = 10    # ≤ 2 000 tokens
SOFT_BAND_FLOOR_LONG = 14      # > 2 000 tokens

# Default soft-band ranges keyed by approximate transcript token size
SOFT_BAND_SHORT = (8, 12)      # ≤ 600 tokens
SOFT_BAND_MEDIUM = (16, 24)    # ≤ 2 000 tokens
SOFT_BAND_LONG = (20, 30)      # > 2 000 tokens

MAX_COMPLETION_TOKENS_LANGUAGE_DETECTION = 120  # token budget for the language-detection call

# Anchor tolerance: ± fraction of anchor_count used to compute soft_lo / soft_hi
ANCHOR_TOLERANCE_FRACTION = 0.15
ANCHOR_TOLERANCE_MIN = 2

# Hard cap on the upper soft-band boundary
SOFT_BAND_HARD_CAP = 40

# Jitter sleep range (seconds) applied between per-language TB calls once anchored
JITTER_SLEEP_LOW = 0.4
JITTER_SLEEP_HIGH = 1.1

DEFAULT_TRANSLATION_MODEL = "gpt-5-mini"  # default model used for subtitle translation
DEFAULT_TONE = "neutral"                  # translation tone/register: "casual" | "neutral" | "formal"
DEFAULT_ERROR_POLICY = "BOUNDED"          # placeholder error policy: "STRICT" | "BOUNDED" | "DEV"

BYTES_TO_TOKENS_RATIO = 0.25          # approximate tokens per byte of SRT source content
TRANSLATION_OVERHEAD_FACTOR = 2.3     # multiplier to account for prompt + system message overhead
PRICE_PER_1K_TOKENS = 0.00015         # estimated cost in USD per 1 000 tokens
AI_CONFIG_BASE_COST = 0.10            # flat estimated cost in USD for one AI config generation run
