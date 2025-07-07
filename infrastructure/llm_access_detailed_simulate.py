"""
@author Jean-Philippe Ulpiano
"""
from pprint import pformat
from typing import List

from infrastructure.llm_access_detailed import LLMAccessDetailed

class LLMAccessDetailedSimulateCalls(LLMAccessDetailed):

    def _send_request_plain(self, messages: List, request_name: str, temperature: float, top_p: float, post_request_name: str) -> str: 
        return {
            'request_name': request_name,
            'response': f"# (Detailed) No calls perfomed\nOriginal request (temperature: {temperature}, top_p: {top_p}, post_request_name: {post_request_name}):\n{pformat(messages)}",
            'temperature': temperature,
            'top_p': top_p ,
            'post_request_name': post_request_name
        }


