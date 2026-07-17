from __future__ import annotations
import os


def force_offline() -> None:
    """强制离线模式，避免 HuggingFace 联网检查在网络/服务故障时无限期挂起。

    BGEM3FlagModel（embedder）、marker-pdf（底层 transformers/surya-ocr）、
    whisperx 加载模型时默认会联网检查版本/配置——这本该是纯本地的一步（模型
    权重由部署脚本预先缓存好），但这几个库都没有暴露任何调用层面的
    local_files_only 之类参数，也没有任何离线兜底或超时：一旦这次联网检查
    连不上（代理故障、断网，或 HuggingFace 官方服务故障），请求会无限期
    挂起，卡死整条入库/解析流程。HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE 这两个
    环境变量是这些库唯一认的开关。

    用 setdefault 而不是硬覆盖：如果调用方已经显式设过这两个变量（比如部署
    脚本首次下载模型时需要临时联网），不会被这里覆盖掉。

    调用时机：必须在真正加载模型之前——理想情况下在脚本最开头、任何
    pipeline 模块被 import 之前调用，这样 whisperx（独立子进程，靠环境变量
    继承）也能拿到。
    """
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
