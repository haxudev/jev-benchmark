"""内网自托管语义决策服务：经 TypeSafe SDK 以 Choice 协议调用，接口与 Jev 官方 API 一致。"""

import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

from typesafe_sdk import (
    Choice, RetryPolicy, TypeSafeClient, TypeSafeAPIError,
    TypeSafeAPIConnectionError, TypeSafeAPIResponseValidationError, TypeSafeAPITimeoutError,
)

from . import ENV_PATH, Decision, ModelError
from .jev_api import parse_choice, read_config


def is_safe_base_url(value: str) -> bool:
    """HTTPS 任意主机；明文 HTTP 仅限私有网段或本机 IP。"""
    try:
        url = urlsplit(value)
        url.port
    except ValueError:
        return False
    if not url.hostname or url.username or url.password or url.query or url.fragment:
        return False
    if url.scheme == "https":
        return True
    if url.scheme != "http":
        return False
    if url.hostname == "localhost":
        return True
    try:
        address = ipaddress.ip_address(url.hostname)
    except ValueError:
        return False
    return address.is_private or address.is_loopback


class IntranetClient:
    key = "intranet"

    def __init__(self, env_path: Path = ENV_PATH) -> None:
        config = read_config(("INTRANET_BASE_URL", "INTRANET_API_KEY", "INTRANET_MODEL"), env_path)
        if not all(config.values()):
            raise ModelError("请在 .env 中设置 INTRANET_BASE_URL、INTRANET_API_KEY、INTRANET_MODEL。")
        if not is_safe_base_url(config["INTRANET_BASE_URL"]):
            raise ModelError("INTRANET_BASE_URL 须为 HTTPS；HTTP 仅允许私有网段或本机 IP，且不能含凭据、查询参数或片段。")
        self._base_url = config["INTRANET_BASE_URL"]
        self._key = config["INTRANET_API_KEY"]
        self.name = config["INTRANET_MODEL"]

    def choose(self, state: str, question: str, options: dict[str, str]) -> Decision:
        if not state.strip() or not question.strip() or not options:
            raise ValueError("对话、问题和候选项不能为空。")
        try:
            with TypeSafeClient(
                base_url=self._base_url,
                api_key=self._key,
                model=self.name,
                timeout=60.0,
                retry=RetryPolicy(max_retries=0),
            ) as client:
                result = client.system_one(
                    state=state,
                    questions={"interpretation": Choice(instructions=question, criteria=options)},
                )
        except TypeSafeAPITimeoutError:
            raise ModelError(f"{self.name} 请求超时（60 秒），未自动重试。") from None
        except TypeSafeAPIConnectionError:
            raise ModelError(f"{self.name} 连接失败，请检查内网服务和 INTRANET_BASE_URL。") from None
        except TypeSafeAPIResponseValidationError:
            raise ModelError(f"{self.name} 返回格式无效，请确认服务支持 Choice。") from None
        except TypeSafeAPIError as error:
            raise ModelError(f"{self.name} 请求失败（HTTP {error.status_code}），请检查密钥及服务状态。") from None
        answer = result.choices.get("interpretation")
        if answer is None:
            raise ModelError(f"{self.name} 响应缺少 interpretation Choice 结果。")
        return parse_choice({
            "model": result.model,
            "answers": {"interpretation": {
                "type": "choice", "choice": answer.choice, "confidence": answer.confidence,
                "probabilities": answer.probabilities,
            }},
        }, options, self.name)
