"""
@author Jean-Philippe Ulpiano
"""
from pprint import pformat
from typing import List

from infrastructure.llm_access import LLMAccess

class LLMAccessSimulateCalls(LLMAccess):

    def _send_request_plain(self, messages: List, request_name: str, temperature: float, top_p: float) -> str: 
        return {
            'request_name': request_name,
            'response': f"# No calls perfomed\nOriginal request (temperature: {temperature}, top_p: {top_p}):\n{pformat(messages)}",
            'temperature': temperature,
            'top_p': top_p
        }


