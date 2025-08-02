#!/usr/bin/env python3
"""
Cache Manager for AI Configuration

Provides caching for:
- AI analysis results
- Configuration validation results
- File content hashes for change detection
- Performance metrics
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSettings


@dataclass
class CacheEntry:
    """A cache entry with metadata."""

    data: Any
    timestamp: float
    file_hashes: Dict[str, str]  # file_path -> hash
    version: str = "1.0"


class CacheManager:
    """Manages caching for AI configuration results."""

    def __init__(self, cache_dir: str = "cache"):
        self.logger = logging.getLogger(__name__)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Cache settings
        self.max_age_hours = 24  # Cache expires after 24 hours
        self.max_cache_size_mb = 100  # Maximum cache size in MB

        # Performance tracking
        self.hit_count = 0
        self.miss_count = 0
        self.total_requests = 0

    def _get_cache_key(self, operation: str, files: List[str]) -> str:
        """Generate a cache key based on operation and file hashes."""
        # Create a hash of the operation and sorted file paths
        key_data = f"{operation}:{':'.join(sorted(files))}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_file_hash(self, file_path: str) -> str:
        """Calculate hash of file content."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not hash file {file_path}: {e}")
            return ""

    def _get_file_hashes(self, files: List[str]) -> Dict[str, str]:
        """Calculate hashes for multiple files."""
        return {file_path: self._get_file_hash(file_path) for file_path in files}

    def _is_cache_valid(
        self, entry: CacheEntry, current_hashes: Dict[str, str]
    ) -> bool:
        """Check if cache entry is still valid."""
        # Check age
        age_hours = (time.time() - entry.timestamp) / 3600
        if age_hours > self.max_age_hours:
            return False

        # Check if file hashes match
        if entry.file_hashes != current_hashes:
            return False

        return True

    def get(self, operation: str, files: List[str]) -> Optional[Any]:
        """Get cached result if available and valid."""
        self.total_requests += 1

        try:
            cache_key = self._get_cache_key(operation, files)
            cache_file = self.cache_dir / f"{cache_key}.json"

            if not cache_file.exists():
                self.miss_count += 1
                return None

            # Load cache entry
            with open(cache_file, "r") as f:
                entry_data = json.load(f)
                entry = CacheEntry(**entry_data)

            # Check if cache is valid
            current_hashes = self._get_file_hashes(files)
            if self._is_cache_valid(entry, current_hashes):
                self.hit_count += 1
                self.logger.info(f"Cache hit for {operation}")
                return entry.data
            else:
                self.miss_count += 1
                self.logger.info(f"Cache miss for {operation} (invalid)")
                # Remove invalid cache
                cache_file.unlink(missing_ok=True)
                return None

        except Exception as e:
            self.logger.warning(f"Error reading cache for {operation}: {e}")
            self.miss_count += 1
            return None

    def set(self, operation: str, files: List[str], data: Any) -> bool:
        """Cache a result."""
        try:
            cache_key = self._get_cache_key(operation, files)
            cache_file = self.cache_dir / f"{cache_key}.json"

            # Create cache entry
            entry = CacheEntry(
                data=data,
                timestamp=time.time(),
                file_hashes=self._get_file_hashes(files),
            )

            # Save to file
            with open(cache_file, "w") as f:
                json.dump(asdict(entry), f, indent=2)

            self.logger.info(f"Cached result for {operation}")

            # Clean up old cache files
            self._cleanup_cache()

            return True

        except Exception as e:
            self.logger.warning(f"Error caching result for {operation}: {e}")
            return False

    def invalidate(self, operation: str = None, files: List[str] = None) -> int:
        """Invalidate cache entries."""
        removed_count = 0

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, "r") as f:
                        entry_data = json.load(f)
                        entry = CacheEntry(**entry_data)

                    # Check if this entry should be invalidated
                    should_remove = False

                    if operation:
                        # Invalidate by operation (would need to decode cache key)
                        pass

                    if files:
                        # Invalidate if any of the specified files are in the entry
                        for file_path in files:
                            if file_path in entry.file_hashes:
                                should_remove = True
                                break

                    if should_remove:
                        cache_file.unlink()
                        removed_count += 1

                except Exception as e:
                    self.logger.warning(
                        f"Error processing cache file {cache_file}: {e}"
                    )
                    # Remove corrupted cache file
                    cache_file.unlink(missing_ok=True)
                    removed_count += 1

            self.logger.info(f"Invalidated {removed_count} cache entries")
            return removed_count

        except Exception as e:
            self.logger.warning(f"Error invalidating cache: {e}")
            return 0

    def _cleanup_cache(self):
        """Remove old cache files to stay within size limits."""
        try:
            # Get all cache files with their sizes and timestamps
            cache_files = []
            total_size = 0

            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    stat = cache_file.stat()
                    cache_files.append((cache_file, stat.st_size, stat.st_mtime))
                    total_size += stat.st_size
                except Exception:
                    continue

            # Convert to MB
            total_size_mb = total_size / (1024 * 1024)

            if total_size_mb <= self.max_cache_size_mb:
                return

            # Sort by timestamp (oldest first)
            cache_files.sort(key=lambda x: x[2])

            # Remove oldest files until under limit
            for cache_file, size, _ in cache_files:
                try:
                    cache_file.unlink()
                    total_size_mb -= size / (1024 * 1024)

                    if total_size_mb <= self.max_cache_size_mb:
                        break

                except Exception as e:
                    self.logger.warning(f"Error removing cache file {cache_file}: {e}")

            self.logger.info(f"Cleaned up cache, size now: {total_size_mb:.1f}MB")

        except Exception as e:
            self.logger.warning(f"Error during cache cleanup: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)

            hit_rate = (
                (self.hit_count / self.total_requests * 100)
                if self.total_requests > 0
                else 0
            )

            return {
                "total_requests": self.total_requests,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate_percent": round(hit_rate, 1),
                "cache_files": len(cache_files),
                "cache_size_mb": round(total_size / (1024 * 1024), 1),
                "max_cache_size_mb": self.max_cache_size_mb,
                "max_age_hours": self.max_age_hours,
            }
        except Exception as e:
            self.logger.warning(f"Error getting cache stats: {e}")
            return {}

    def clear_all(self) -> int:
        """Clear all cache files."""
        try:
            removed_count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    removed_count += 1
                except Exception:
                    pass

            self.logger.info(f"Cleared {removed_count} cache files")
            return removed_count

        except Exception as e:
            self.logger.warning(f"Error clearing cache: {e}")
            return 0
