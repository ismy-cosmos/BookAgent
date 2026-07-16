"""跨 ImportQueue 和 ask() 路由共享的忙碌状态原语（issue #36）。

两者都是使用方，不再各自维护一份独立的"忙碌吗"状态——旧设计里 ImportQueue
私有的 busy 状态只挡得住导入互相撞车，ask() 完全不知道这个状态存在，也不会
把自己的忙碌状态告诉任何人，导致"回答问题时能同时开始导入"这个缺口。
"""
from __future__ import annotations
import threading
from dataclasses import dataclass
from typing import Literal, Optional

BusyReason = Literal["ingesting", "answering"]


@dataclass(frozen=True)
class BusyState:
    reason: BusyReason
    book_id: Optional[str]


_lock = threading.Lock()
_state: Optional[BusyState] = None


def try_acquire(reason: BusyReason, book_id: Optional[str]) -> Optional[BusyState]:
    """尝试获取忙碌状态。成功返回 None；失败返回当前占用者的状态——
    获取和"查询失败原因"在同一次加锁内原子完成，调用方不需要另外再查一次
    （避免"检查完再读一次、中间状态已经变了"的竞态），可以直接用返回值
    生成精确的报错文案。"""
    global _state
    with _lock:
        if _state is not None:
            return _state
        _state = BusyState(reason=reason, book_id=book_id)
        return None


def release() -> None:
    global _state
    with _lock:
        _state = None


def get_state() -> Optional[BusyState]:
    with _lock:
        return _state
