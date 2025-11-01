from __future__ import annotations

from typing import Any, Callable, List, Sequence, TypeVar

CallableReturnT = TypeVar("CallableReturnT")


class RetryError(Exception):
    """
    Raised when the retry helper exhausts all attempts without success.

    Attributes:
        exceptions: Ordered list of the exceptions raised by each attempt.
    """

    def __init__(self, exceptions: Sequence[BaseException]) -> None:
        message = f"Retry failed after {len(exceptions)} attempts."
        super().__init__(message)
        self.exceptions: List[BaseException] = list(exceptions)


def retry(
    function: Callable[..., CallableReturnT],
    driver: Any,
    *call_args: Any,
    attempts: int = 3,
    driver_factory: Callable[[], Any] | None = None,
    before_retry: Callable[[Any, BaseException], None] | None = None,
    **call_kwargs: Any,
) -> CallableReturnT:
    """
    Execute `function` with a fresh driver up to `attempts` times.

    Args:
        function: Callable that accepts a driver as its first positional argument.
        driver: Either a WebDriver instance for the first attempt or a callable that
            returns one when invoked.
        *call_args: Positional arguments forwarded to `function` after the driver.
        attempts: Total number of tries (defaults to 3).
        driver_factory: Optional callable that creates a fresh driver for retries when
            a driver instance is supplied as `driver`.
        before_retry: Optional callback invoked after each exception and before the
            next retry; receives the current driver and the raised exception.
        **call_kwargs: Keyword arguments forwarded to `function`.

    Raises:
        RetryError: When all attempts fail; contains the collected exceptions.
        ValueError: When attempts is less than 1.
    """

    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    failures: List[BaseException] = []

    factory = driver_factory
    if callable(driver) and not hasattr(driver, "quit"):
        factory = driver  # treat callable driver as factory
        current_driver = factory()
    else:
        current_driver = driver

    for attempt in range(1, attempts + 1):
        try:
            return function(current_driver, *call_args, **call_kwargs)
        except Exception as exc:
            failures.append(exc)

            if attempt < attempts:
                if before_retry is not None:
                    try:
                        before_retry(current_driver, exc)
                    except Exception as callback_exc:
                        failures.append(callback_exc)

                try:
                    current_driver.quit()
                except Exception as quit_exc:
                    failures.append(quit_exc)

                if factory is None:
                    break

                try:
                    current_driver = factory()
                except Exception as creation_error:
                    failures.append(creation_error)
                    break
            else:
                try:
                    current_driver.quit()
                except Exception as quit_exc:
                    failures.append(quit_exc)

    raise RetryError(failures)
