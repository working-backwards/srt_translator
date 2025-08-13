# Architecture Violations and Solutions for GUI-Core Engine Communication

## 🚨 Problem Statement

The current `gui/workers/translation_worker.py` violates critical architecture principles by directly importing and calling core engine modules. This creates tight coupling between the GUI and core engine, violating the clean separation we've established.

Clients import only `srt_translator.api` (public), not `srt_translator.core.*` (internal).

## 🔍 Current Violations

### **Violation 1: Direct Core Engine Imports in GUI Module**

```python
# ❌ VIOLATION: GUI importing core engine modules
from srt_translator.core.config.models import TranslationConfig
from srt_translator.core.translator.fixer import SRTFixer
from srt_translator.core.main import translate_srt_files
```

**Why This Violates Architecture:**
- Violates the principle: "Core engine ONLY reads from TranslationConfig objects passed as parameters"

### **Violation 2: GUI Calling Core Engine Functions Directly**

```python
# ❌ VIOLATION: GUI calling core engine directly
results = translate_srt_files(
    file_paths=self.selected_files, config=config
)

# ❌ VIOLATION: GUI creating core engine objects directly
fixer = SRTFixer(log_file, batch_dir)
```

**Why This Violates Architecture:**
- GUI has intimate knowledge of core engine internals
- Core engine functions are called from GUI context
- Violates separation of concerns

## 🎯 Requirements for Long Batch Communication

Based on your requirements, the GUI needs to communicate with the core engine during long batches to:

1. **Show batch is running**: Progress bar moving back and forth
2. **Display status messages**: Real-time updates in the text area below "Translate All Files"
3. **Indicate completion**: Clear signal when batch finishes
4. **Detect hung state**: Identify when batch is stuck
5. **Maintain simplicity**: Easy to maintain and write
6. **Ensure reliability**: Rock solid, no failures

## 🛠️ Proposed Solutions

### **Option 1: Callback/Progress Interface Pattern**

**How it works:**
- Core engine accepts a progress callback function
- GUI passes a callback that updates the UI
- Core engine calls callback during processing

**Code Example:**
```python
# Core engine interface
def translate_srt_files(
    file_paths: List[str], 
    config: TranslationConfig,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    # ... translation logic ...
    if progress_callback:
        progress_callback(f"Processing {filename}...")
    
# GUI usage
def update_progress(message: str):
    self.progress_updated.emit(message)

results = translate_srt_files(
    file_paths=self.selected_files, 
    config=config,
    progress_callback=update_progress
)
```

**Pros:**
- Simple to implement
- Direct communication
- Easy to understand

**Cons:**
- Still couples GUI to core engine interface
- Callback functions can be complex to manage
- Harder to test

### **Option 2: Event-Driven Message Bus Pattern**

**How it works:**
- Create a message bus/event system
- Core engine emits events during processing
- GUI subscribes to events and updates UI

**Code Example:**
```python
# Message bus interface
class TranslationEventBus:
    def emit(self, event_type: str, data: Any) -> None:
        # Emit event to all subscribers
        
    def subscribe(self, event_type: str, callback: Callable) -> None:
        # Subscribe to specific event types

# Core engine usage
event_bus.emit("file_started", {"filename": "example.srt"})
event_bus.emit("translation_progress", {"message": "Processing subtitle 45..."})

# GUI usage
event_bus.subscribe("file_started", self.on_file_started)
event_bus.subscribe("translation_progress", self.on_progress_update)
```

**Pros:**
- Loose coupling
- Easy to add new event types
- Good for testing

**Cons:**
- More complex to implement
- Event ordering can be tricky
- Potential for memory leaks if not managed properly

### **Option 3: Status Object with Polling Pattern**

**How it works:**
- Core engine maintains a status object
- GUI polls the status object periodically
- Status object contains current state, progress, and messages

**Code Example:**
```python
# Status object
@dataclass
class TranslationStatus:
    is_running: bool
    current_file: str
    current_message: str
    total_files: int
    processed_files: int
    errors: List[str]
    is_complete: bool

# Core engine updates status
self.status.current_file = filename
self.status.current_message = f"Processing {filename}..."

# GUI polls status
def check_status(self):
    if self.translation_status.is_running:
        self.update_progress(self.translation_status.current_message)
        if self.translation_status.is_complete:
            self.on_translation_complete()
```

**Pros:**
- Simple to implement
- No complex event handling
- Easy to debug

**Cons:**
- Polling overhead
- Potential for missed updates
- Less responsive than real-time events

### **Option 4: Queue-Based Message Pattern**

**How it works:**
- Core engine puts messages in a thread-safe queue
- GUI worker thread reads from queue and updates UI
- Messages flow through a clean interface

**Code Example:**
```python
# Message interface
@dataclass
class TranslationMessage:
    message_type: str  # "progress", "error", "complete"
    content: str
    timestamp: datetime

# Core engine interface
class TranslationInterface:
    def __init__(self, message_queue: Queue[TranslationMessage]):
        self.message_queue = message_queue
    
    def send_progress(self, message: str):
        self.message_queue.put(TranslationMessage("progress", message, datetime.now()))

# GUI worker reads from queue
def process_messages(self):
    while not self.message_queue.empty():
        msg = self.message_queue.get_nowait()
        if msg.message_type == "progress":
            self.progress_updated.emit(msg.content)
```

**Pros:**
- Clean separation of concerns
- Thread-safe communication
- Easy to test and debug

**Cons:**
- Slightly more complex than callbacks
- Need to manage queue lifecycle

## 🏆 Recommendation: Option 4 (Queue-Based Message Pattern)

**Why This is the Best Solution:**

1. **Clean Architecture**: Maintains separation between GUI and core engine
2. **Simplicity**: Easy to understand and implement
3. **Reliability**: Thread-safe, no race conditions
4. **Maintainability**: Clear interface, easy to modify
5. **Testability**: Can easily mock the message queue for testing

**Implementation Strategy:**

1. **Create a clean interface** that core engine implements
2. **Use existing Qt signals** for UI updates (no new patterns)
3. **Keep the message queue simple** - just strings and basic metadata
4. **Leverage existing worker thread** for message processing

**Key Benefits:**
- Core engine never imports GUI modules
- GUI never imports core engine modules
- Communication happens through a simple, typed interface
- Easy to add new message types
- Rock solid reliability with thread safety

## 🔧 Implementation Steps

1. **Create TranslationInterface** in core engine
2. **Implement message queue** in GUI worker
3. **Update core engine** to use interface
4. **Update GUI worker** to read from queue
5. **Test thoroughly** with long batches
6. **Document the interface** for future developers

This solution gives you the simplicity and reliability you want while maintaining clean architecture boundaries.
