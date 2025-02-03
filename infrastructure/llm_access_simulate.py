from pprint import pformat
from typing import List

from infrastructure.llm_access import LLMAccess

class LLMAccessSimulateCalls(LLMAccess):

    def _send_request_plain(self, messages: List, request_name: str) -> str: 
        return {
            'request_name': request_name,
            'response': f"# No calls perfomed\nOriginal request:\n{pformat(messages)}" 
        }


