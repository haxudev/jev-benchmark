"""Microsoft Decision 的原生 System One 接口。"""

from .jev_api import JevClient


class MicrosoftClient(JevClient):
    key = "microsoft"
    name = "Microsoft Decision"
    config_prefix = "MICROSOFT"
    default_endpoint = (
        "https://func-meter-g4i4ocbcoq4pq.azurewebsites.net"
        "/providers/microsoft/v1/systemone"
    )
    model = "Decision-1"

    def accepts_model(self, actual: object) -> bool:
        if not isinstance(actual, str):
            return False
        expected = {self.model.casefold()}
        if self.model.casefold() == "decision-1":
            expected.add("microsoft-decision-1")
        return actual.casefold() in expected
