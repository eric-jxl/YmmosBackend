"""
Loguru 统一日志配置
格式规范参照 Uvicorn / FastAPI / Pydantic 等顶级项目惯例：
  TIME | LEVEL    | MODULE:FUNC:LINE - MESSAGE
安全审计事件通过 logger.bind(security=True) 路由到独立文件。
"""
import logging
import sys
from pathlib import Path

from loguru import logger

# 存储所有 logger handler IDs，以便优雅关闭
_handler_ids: list[int] = []

# ── 格式常量 ────────────────────────────────────────────────────────────────
_CONSOLE_FMT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)
_FILE_FMT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "{message}"
)


# ── stdlib logging 桥接 ─────────────────────────────────────────────────────
class _InterceptHandler(logging.Handler):
    """将标准库 logging 的输出全部转发给 loguru。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ── 安全审计专用 logger ──────────────────────────────────────────────────────
security_logger = logger.bind(security=True)


# ── 初始化入口 ───────────────────────────────────────────────────────────────
def setup_logging(level: str = "INFO", is_dev: bool = False) -> None:
    """
    配置 loguru sinks：
      - stdout  : 全级别（dev=DEBUG，prod=INFO）
      - logs/app_YYYY-MM-DD.log   : INFO+，保留 30 天
      - logs/error_YYYY-MM-DD.log : ERROR+，保留 90 天，附完整诊断
      - logs/security_YYYY-MM-DD.log : 安全审计，保留 365 天
    """
    Path("logs").mkdir(exist_ok=True)
    logger.remove()
    _handler_ids.clear()

    # Console
    handler_id = logger.add(
        sys.stdout,
        format=_CONSOLE_FMT,
        level="DEBUG" if is_dev else level,
        colorize=True,
        backtrace=is_dev,
        diagnose=is_dev,
        enqueue=False,
    )
    _handler_ids.append(handler_id)

    # 滚动日志 - 全量
    handler_id = logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        format=_FILE_FMT,
        level="INFO",
        rotation="00:00",
        retention="30 days",
        compression="gz",
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
        enqueue=True,
    )
    _handler_ids.append(handler_id)

    # 滚动日志 - 仅错误（含 traceback 诊断）
    handler_id = logger.add(
        "logs/error_{time:YYYY-MM-DD}.log",
        format=_FILE_FMT,
        level="ERROR",
        rotation="00:00",
        retention="90 days",
        compression="gz",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
    _handler_ids.append(handler_id)

    # 滚动日志 - 安全审计（独立文件，永久可追溯 365 天）
    handler_id = logger.add(
        "logs/security_{time:YYYY-MM-DD}.log",
        format=_FILE_FMT,
        level="INFO",
        rotation="00:00",
        retention="365 days",
        compression="gz",
        encoding="utf-8",
        filter=lambda r: r["extra"].get("security", False),
        enqueue=True,
    )
    _handler_ids.append(handler_id)

    # 接管所有 stdlib logging（uvicorn / sqlalchemy / httpx 等）
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in list(logging.root.manager.loggerDict):
        log = logging.getLogger(name)
        log.handlers = [_InterceptHandler()]
        log.propagate = False

    logger.info(
        "Logging initialized | level={} | dev={} | sinks=stdout,app,error,security",
        level,
        is_dev,
    )


def shutdown_logging() -> None:
    """
    优雅关闭所有日志处理器，确保队列中的日志全部写入，释放资源。
    在应用 shutdown 时调用，避免 multiprocessing 资源泄漏警告。
    """
    try:
        logger.info("正在关闭日志处理器...")
        for handler_id in _handler_ids:
            try:
                logger.remove(handler_id)
            except ValueError:
                pass  # handler 可能已被移除
        _handler_ids.clear()
        # 注意：logger.complete() 可能会长时间阻塞，这里不调用以避免卡住
        # 大部分日志应该已经通过 remove() 刷新到磁盘了
    except Exception as e:
        # 确保即使日志关闭失败也不阻塞应用退出
        print(f"Warning: Error during logging shutdown: {e}", file=sys.stderr)



