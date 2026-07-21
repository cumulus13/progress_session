#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# progress_session.py
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 cumulus13 (cumulus13@gmail.com)
# A Python requests session with progress and retry capabilities
# SPDX-FileCopyrightText: 2025 cumulus13 <cumulus13@gmail.com>

from __future__ import annotations
from typing import Optional, Any, Set, Union
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
import requests
from requests.exceptions import (
    ConnectionError, 
    Timeout, 
    ReadTimeout,
    ConnectTimeout,
    HTTPError,
    RequestException,
    ChunkedEncodingError,
    ContentDecodingError,
    TooManyRedirects
)
import time
from rich.syntax import Syntax
import traceback
import os
import sys
import threading
import re
import logging
from urllib.parse import urljoin, urlparse
import socket

console = Console()

LOG_LEVEL = "CRITICAL"
SHOW_LOG = False
logger = None

if (len(sys.argv) > 1 and any('--debug' == arg for arg in sys.argv[1:])) or str(os.getenv('PPROGRESS_SESSION_DEBUG', os.getenv('DEBUG', False))).lower() in ['1', 'true', 'ok', 'on', 'yes']:
    print("🐞 Debug mode enabled [progress_session]")
    os.environ["DEBUG"] = "1"
    os.environ['LOGGING'] = "1"
    os.environ.pop('NO_LOGGING', None)
    os.environ['TRACEBACK'] = "1"
    SHOW_LOG = True
    LOG_LEVEL="DEBUG"

    print(f"LOG_LEVEL: {LOG_LEVEL}")
    print(f"SHOW_LOG: {SHOW_LOG}")
    print(f"os.getenv('DEBUG'): {os.getenv('DEBUG', '0')}")
    print(f"os.getenv('LOGGING'): {os.getenv('LOGGING', '0')}")
    print(f"os.getenv('NO_LOGGING'): {os.getenv('NO_LOGGING', '0')}")

    try:
        from richcolorlog import setup_logging  # type: ignore
        logger = setup_logging('progress_session', level=LOG_LEVEL, show = SHOW_LOG)
    except:
        import logging

        LOG_LEVEL = getattr(logging, os.getenv('LOG_LEVEL', LOG_LEVEL).upper(), 1000)
        
        try:
            from .custom_logging import get_logger  # type: ignore
        except ImportError:
            from custom_logging import get_logger  # type: ignore
        
        try:
            logger = get_logger('progress_session', level=LOG_LEVEL)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.setLevel(LOG_LEVEL)

    print(f"LOG_LEVEL: {LOG_LEVEL}")
    print(f"SHOW_LOG: {SHOW_LOG}")
    print(f"os.getenv('DEBUG'): {os.getenv('DEBUG', '0')}")
    print(f"os.getenv('LOGGING'): {os.getenv('LOGGING', '0')}")
    print(f"os.getenv('NO_LOGGING'): {os.getenv('NO_LOGGING', '0')}")
else:
    import logging

    LOG_LEVEL = getattr(logging, os.getenv('LOG_LEVEL', LOG_LEVEL).upper(), 1000)
    
    try:
        from .custom_logging import get_logger  # type: ignore
    except ImportError:
        from custom_logging import get_logger  # type: ignore
    
    try:
        logger = get_logger('progress_session', level=LOG_LEVEL)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.setLevel(LOG_LEVEL)

class ProgressSession(requests.Session):
    """
    Enhanced requests.Session with progress display and robust retry logic.
    
    Features:
    - Visual progress indicator with Rich
    - Intelligent retry with exponential backoff
    - Smart retry decision based on error type
    - Connection pool management with cleanup
    - Optional URL masking for security
    - Thread-safe request execution
    
    Args:
        base_url: Base URL for relative paths
        default_text: Default progress text
        show_url: Show full URLs in progress/errors (default: from SHOW_URL env)
        pool_connections: Connection pool size (default: 10)
        pool_maxsize: Max pool size (default: 10)
        max_retries_adapter: Retry adapter for connection pool (default: 0, we handle retries)
        *args, **kwargs: Passed to requests.Session
    """
    
    # Error types yang HARUS di-retry (transient errors)
    RETRYABLE_ERRORS: Set[type] = {
        ConnectionError,
        ConnectTimeout,
        ReadTimeout,
        Timeout,
        ChunkedEncodingError,
        ContentDecodingError,
        socket.timeout,
        socket.gaierror,  # DNS resolution error
        requests.exceptions.ConnectionError,
    }
    
    # HTTP status codes yang bisa di-retry
    RETRYABLE_STATUS_CODES: Set[int] = {
        408,  # Request Timeout
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
        507,  # Insufficient Storage
        509,  # Bandwidth Limit Exceeded
        599,  # Network Connect Timeout Error
    }
    
    # Error types that cannot be retried (permanent errors)
    NON_RETRYABLE_ERRORS: Set[type] = {
        TooManyRedirects,
        ValueError,
        TypeError,
    }
    
    def __init__(
        self, 
        base_url: Optional[str] = None, 
        default_text: str = "Connecting",
        show_url: Optional[bool] = None,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        max_retries_adapter: int = 0,
        disable: bool = False,
        *args, 
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.base_url = base_url
        self.default_text = default_text
        self.disable = disable
        
        # Determine show_url: explicit param > env var > False
        if show_url is not None:
            self._show_url = show_url
        else:
            self._show_url = os.getenv('SHOW_URL', '0').lower() in ['1', 'true']
        
        # Setup connection pooling with adapter
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=max_retries_adapter,
            pool_block=False
        )
        self.mount('http://', adapter)
        self.mount('https://', adapter)
        
        # Keep alive configuration
        self.keep_alive = True
        
        logger.info(
            f"ProgressSession initialized: pool_connections={pool_connections}, pool_maxsize={pool_maxsize}"
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        try:
            self.close()
            logger.debug("ProgressSession closed and connections cleaned up")
        except Exception as e:
            logger.error(f"Error while closing ProgressSession: {e}")

    def _should_retry(self, exception: Exception, status_code: Optional[int] = None) -> tuple[bool, str]:
        """
        Intelligent decision: apakah error ini harus di-retry atau tidak.
        
        Returns:
            (should_retry: bool, reason: str)
        """
        # Check exception type
        exc_type = type(exception)
        
        # Non-retryable errors (permanent failures)
        if exc_type in self.NON_RETRYABLE_ERRORS:
            return False, f"Non-retryable error: {exc_type.__name__}"
        
        # Retryable errors (transient failures)
        if exc_type in self.RETRYABLE_ERRORS:
            return True, f"Retryable error: {exc_type.__name__}"
        
        # Check if it's a subclass of retryable errors
        for retryable_type in self.RETRYABLE_ERRORS:
            if isinstance(exception, retryable_type):
                return True, f"Retryable error (subclass): {exc_type.__name__}"
        
        # HTTP status code based retry
        if status_code and status_code in self.RETRYABLE_STATUS_CODES:
            return True, f"Retryable HTTP status: {status_code}"
        
        # 4xx errors (except 408, 429) are NOT retryable
        if status_code and 400 <= status_code < 500 and status_code not in self.RETRYABLE_STATUS_CODES:
            return False, f"Client error (4xx): {status_code}"
        
        # Check for specific error messages (connection issues)
        error_msg = str(exception).lower()
        connection_keywords = [
            'connection', 'timed out', 'timeout', 'refused',
            'reset', 'broken pipe', 'network', 'unreachable',
            'dns', 'resolve', 'getaddrinfo'
        ]
        
        if any(keyword in error_msg for keyword in connection_keywords):
            return True, f"Connection issue detected in error message"
        
        # Default: retry untuk unknown errors (better safe than sorry)
        return True, f"Unknown error, attempting retry: {exc_type.__name__}"
    
    def _build_url(self, url: str) -> str:
        """
        Safely combine base_url with provided url.
        
        Rules:
        - If url is absolute (has scheme), use it as-is
        - If url is relative and base_url exists, join them
        - Otherwise use url as-is
        """
        if not url:
            raise ValueError("URL cannot be empty")
        
        # If URL has scheme (http/https), it's absolute - use as-is
        if urlparse(url).scheme:
            return url
        
        # If we have base_url and url is relative, join them
        if self.base_url:
            return urljoin(self.base_url, url)
        
        return url
    
    def _mask_url(self, text: str) -> str:
        """
        Mask URLs in text for security.
        Only masks actual URLs, not file paths or version strings.
        """
        if self._show_url:
            return text
        
        # Mask http(s) URLs
        text = re.sub(
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            '[MASKED-URL]',
            text
        )
        
        # Mask domain-like patterns only if they look like URLs
        text = re.sub(
            r'\b(?:www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s<>"{}|\\^`\[\]]*)?',
            '[MASKED-URL]',
            text
        )
        
        return text
    
    def _format_exception_message(self, exc: Exception) -> str:
        """Format exception message with optional URL masking."""
        exc_str = str(exc)
        return self._mask_url(exc_str)
    
    def _calculate_retry_delay(
        self, 
        attempt: int, 
        base_delay: float, 
        exponential_backoff: bool,
        max_delay: float = 60.0,
        jitter: bool = True
    ) -> float:
        """
        Calculate smart retry delay with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number (1-based)
            base_delay: Base delay in seconds
            exponential_backoff: Use exponential backoff
            max_delay: Maximum delay cap
            jitter: Add random jitter to prevent thundering herd
        
        Returns:
            Delay in seconds
        """
        if exponential_backoff:
            # Exponential: base * 2^(attempt-1)
            delay = base_delay * (2 ** (attempt - 1))
        else:
            # Linear: base * attempt
            delay = base_delay * attempt
        
        # Cap at max_delay
        delay = min(delay, max_delay)
        
        # Add jitter (0-25% of delay) to prevent thundering herd
        if jitter:
            import random
            jitter_amount = delay * 0.25
            delay += random.uniform(0, jitter_amount)
        
        return delay
    
    def _cleanup_connection(self):
        """Force cleanup of stale connections."""
        try:
            # Close all adapters and their connection pools
            for adapter in self.adapters.values():
                adapter.close()
            logger.debug("Connection pools cleaned up")
        except Exception as e:
            logger.warning(f"Error during connection cleanup: {e}")
    
    def request(
        self, 
        method: str, 
        url: str, 
        *args,
        max_try: int = 3,
        retry_delay: float = 1.0,
        text: Optional[str] = None,
        theme: str = 'monokai',
        show_traceback: Optional[bool] = None,
        exponential_backoff: bool = True,
        max_retry_delay: float = 60.0,
        retry_jitter: bool = True,
        cleanup_on_retry: bool = True,
        disable: bool = False,
        **kwargs
    ) -> Optional[Union[requests.Response, RequestException]]:
        """
        Make HTTP request with progress display and intelligent retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request (absolute or relative to base_url)
            max_try: Maximum number of attempts (default: 3)
            retry_delay: Initial delay between retries in seconds (default: 1.0)
            text: Progress text (default: from constructor)
            theme: Syntax highlighting theme for errors (default: 'monokai')
            show_traceback: Show full traceback on error (default: from TRACEBACK env)
            exponential_backoff: Use exponential backoff for retries (default: True)
            max_retry_delay: Maximum retry delay cap in seconds (default: 60.0)
            retry_jitter: Add random jitter to retry delays (default: True)
            cleanup_on_retry: Cleanup connections before retry (default: True)
            *args, **kwargs: Passed to requests.Session.request
            
        Returns:
            requests.Response object
            
        Raises:
            Exception: Last exception if all retries fail or non-retryable error
        """

        self.disable = self.disable or disable
        # Build final URL
        try:
            full_url = self._build_url(url)
        except ValueError as e:
            console.print(f"[red bold]ERROR:[/] {e}")
            raise
        
        # Determine display text
        display_text = text or self.default_text
        
        # Determine if we should show traceback
        if show_traceback is None:
            show_traceback = str(os.getenv('TRACEBACK', '0')).lower() in ['1', 'true']
        
        # Display URL (masked if needed)
        display_url = self._mask_url(full_url) if not self._show_url else full_url
        
        attempt = 0
        last_exception = None
        dot_cycle = ['.', '..', '...']
        dot_index = 0
        dots = ''
        
        # Ensure timeout is set (prevent hanging forever)
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30  # Default 30 seconds
            logger.debug(f"No timeout specified, using default: {kwargs['timeout']}s")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
            refresh_per_second=12,
            disable=self.disable
        ) as progress:
            task = progress.add_task(f"[yellow]{display_text}[/]", total=None)
            
            while attempt < max_try:
                attempt += 1
                
                # Thread-safe request execution
                response_holder = {'response': None, 'exception': None}
                done_event = threading.Event()
                
                def do_request():
                    try:
                        response_holder['response'] = super(ProgressSession, self).request(  # type: ignore
                            method, full_url, *args, **kwargs
                        )
                    except Exception as e:
                        response_holder['exception'] = e  # type: ignore
                    finally:
                        done_event.set()
                
                req_thread = threading.Thread(target=do_request, daemon=True)
                req_thread.start()
                
                # Animate progress while request is running
                while not done_event.is_set():
                    dots = dot_cycle[dot_index]
                    dot_index = (dot_index + 1) % len(dot_cycle)
                    progress.update(
                        task,
                        description=(
                            f"[yellow]Attempt[/] [#AA55FF]{attempt}[/]"
                            f"/[#0055FF]{max_try}[/]: "
                            f"[#FFFF00]{method.upper()}[/] "
                            f"[#FF5500]{display_url}[/] "
                            f"[#00FFFF]{dots}[/]"
                        )
                    )
                    done_event.wait(timeout=0.2)
                
                # Ensure thread is finished
                req_thread.join(timeout=1.0)
                
                # Check if thread is still alive (shouldn't happen)
                if req_thread.is_alive():
                    logger.error("Request thread did not finish in time!")
                
                # Check results
                logger.warning(f"response_holder: {response_holder}")
                if response_holder['exception']:
                    last_exception = response_holder['exception']
                    error_msg = self._format_exception_message(last_exception)
                    
                    # Decide if we should retry this error
                    should_retry, retry_reason = self._should_retry(last_exception)
                    
                    progress.update(
                        task, 
                        description=(
                            f"[red]Attempt[/] [#AA55FF]{attempt}[/]"
                            f"/[#0055FF]{max_try}[/]: "
                            f"[#FFFF00]{method.upper()}[/] "
                            f"[#FF5500]{display_url}[/] "
                            f"[#FF007F]Failed[/] - {error_msg[:50]}"
                        )
                    )
                    
                    logger.warning(
                        f"Request failed (attempt {attempt}/{max_try}): "
                        f"{type(last_exception).__name__}: {error_msg[:100]}"
                    )
                    logger.debug(f"Retry decision: {retry_reason}")
                    
                    # If non-retryable or last attempt, fail immediately
                    if not should_retry:
                        logger.error(f"Non-retryable error detected: {retry_reason}")
                        break
                
                    logger.debug(f"attempt [1]: {attempt}")
                    logger.debug(f"max_try [1]: {max_try}")
                    
                    if attempt >= max_try:
                        logger.error(f"Max retries ({max_try}) reached")
                        break
                    
                    # Cleanup connections before retry (helps with stale connections)
                    if cleanup_on_retry:
                        logger.debug("Cleaning up connections before retry")
                        self._cleanup_connection()
                    
                    # Calculate and apply retry delay
                    delay = self._calculate_retry_delay(
                        attempt=attempt,
                        base_delay=retry_delay,
                        exponential_backoff=exponential_backoff,
                        max_delay=max_retry_delay,
                        jitter=retry_jitter
                    )
                    
                    logger.info(f"Retrying in {delay:.2f}s... ({retry_reason})")
                    time.sleep(delay)
                    continue
                
                # Success case - check HTTP status
                response = response_holder['response']
                logger.debug(f"attempt [2]: {attempt}")
                logger.debug(f"max_try [2]: {max_try}")
                try:
                    try:
                        response.raise_for_status()  # type: ignore
                    except Exception as e:
                        if attempt >= max_try:
                            if str(os.getenv('TRACEBACK', '0')).lower() in ['1', 'true', 'ok', 'yes']:
                                console.print_exception(width=os.get_terminal_size()[0])
                            # return requests.Response()  # type: ignore
                            return RequestException(f"Final attempt failed: {e}")  # type: ignore
                    progress.update(
                        task,
                        description=(
                            f"[green]Success[/]: "
                            f"[#FFFF00]{method.upper()}[/] "
                            f"[#FF5500]{display_url}[/] "
                            f"[#00FF00]✓[/] [{response.status_code if response else 404}]"
                        )
                    )
                    logger.info(f"Request successful: {method} {display_url} - {response.status_code if response else 'No Response'}")
                    return response
                    
                except HTTPError as e:
                    last_exception = e
                    status_code = response.status_code  # type: ignore
                    error_msg = self._format_exception_message(e)
                    
                    # Decide if we should retry based on status code
                    should_retry, retry_reason = self._should_retry(e, status_code)
                    
                    progress.update(
                        task,
                        description=(
                            f"[red]HTTP {status_code}[/]: "
                            f"[#FFFF00]{method.upper()}[/] "
                            f"[#FF5500]{display_url}[/]"
                        )
                    )
                    
                    logger.warning(
                        f"HTTP error {status_code} (attempt {attempt}/{max_try}): {error_msg[:100]}"
                    )
                    logger.debug(f"Retry decision: {retry_reason}")
                    
                    # If non-retryable or last attempt, fail
                    if not should_retry or attempt >= max_try:
                        if not should_retry:
                            logger.error(f"Non-retryable HTTP error: {retry_reason}")
                        break
                    
                    # Cleanup and retry
                    if cleanup_on_retry:
                        self._cleanup_connection()
                    
                    delay = self._calculate_retry_delay(
                        attempt=attempt,
                        base_delay=retry_delay,
                        exponential_backoff=exponential_backoff,
                        max_delay=max_retry_delay,
                        jitter=retry_jitter
                    )
                    
                    logger.info(f"Retrying in {delay:.2f}s... ({retry_reason})")
                    time.sleep(delay)
                    continue
            
            # All retries exhausted or non-retryable error
            progress.update(
                task,
                description=(
                    f"[white on red]Failed after {attempt} attempt(s)[/]: "
                    f"[#FFFF00]{method.upper()}[/] "
                    f"[#FF5500]{display_url}[/]"
                )
            )
            
            # Display error information
            if last_exception:
                error_msg = self._format_exception_message(last_exception)
                
                if show_traceback:
                    tb_text = ''.join(traceback.format_exception(
                        type(last_exception),
                        last_exception,
                        last_exception.__traceback__
                    ))
                    tb_text = self._mask_url(tb_text)
                    tb = Syntax(tb_text, 'python', line_numbers=True, theme=theme)
                    console.print(tb)
                else:
                    console.print(f"[red bold]ERROR:[/] {error_msg}")
                    console.print(
                        "[dim]Set TRACEBACK=1 or show_traceback=True for full traceback[/]"
                    )
                
                logger.error(f"Request failed permanently: {type(last_exception).__name__}: {error_msg}")
                
                # Re-raise the original exception
                raise last_exception
            else:
                error_msg = f"Request failed after {attempt} attempts with no exception captured"
                logger.error(error_msg)
                raise RuntimeError(error_msg)


# Example usage and tests
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("ROBUST CONNECTION & RETRY TESTS")
    print("="*70)
    
    # Test 1: Connection timeout (retryable)
    print("\n[Test 1] Connection Timeout (Should Retry):")
    with ProgressSession() as session:
        try:
            response = session.get(
                "https://httpbin.org/delay/5",
                timeout=2,
                max_try=3,
                retry_delay=0.5
            )
        except Exception as e:
            print(f"  Expected failure: {type(e).__name__}")
    
    # Test 2: 404 error (non-retryable)
    print("\n[Test 2] 404 Error (Should NOT Retry):")
    with ProgressSession() as session:
        try:
            response = session.get(
                "https://httpbin.org/status/404",
                max_try=3
            )
        except Exception as e:
            print(f"  Expected quick failure: {type(e).__name__}")
    
    # Test 3: 503 error (retryable)
    print("\n[Test 3] 503 Service Unavailable (Should Retry):")
    with ProgressSession() as session:
        try:
            response = session.get(
                "https://httpbin.org/status/503",
                max_try=3,
                retry_delay=0.5
            )
        except Exception as e:
            print(f"  Expected failure after retries: {type(e).__name__}")
    
    # Test 4: Successful request
    print("\n[Test 4] Successful Request:")
    with ProgressSession() as session:
        try:
            response = session.get("https://httpbin.org/get", timeout=10)
            print(f"  ✓ Success: {response.status_code}")
        except Exception as e:
            print(f"  Unexpected failure: {e}")
    
    print("\n" + "="*70)
    print("Tests completed!")
    print("="*70)