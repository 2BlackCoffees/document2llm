"""
@author Jean-Philippe Ulpiano
"""
from abc import abstractmethod, ABC
from typing import List
import json
from logging import Logger
from domain.ichecker import IChecker
from domain.llm_utils import LLMUtils

class ContextWindowExceededError(Exception):
    pass

class AbstractLLMAccess(ABC):
    def __init__(self, logger: Logger, reviewer: str, model_name: str, llm_utils: LLMUtils): 
        self.reviewer = reviewer
        self.logger = logger
        self.checker = None
        self.model_name = model_name # "llama3-70b"  # or use gpt-4o-mini, gpt-4o as per access requested
        self.llm_utils = llm_utils

    def set_checker(self, checker: IChecker):
        self.checker = checker

    @abstractmethod
    def _prepare_and_send_requests(self, request_inputs: List) -> List:
        """
        """
    @abstractmethod
    def _send_request_plain(self, messages: List, request_name: str, temperature: float, top_p: float, post_request_name: str) -> str: 
        """
        """

    def check(self, slide_content: List, requires_format_description: bool) -> List:
        if self.checker is None:
            raise Exception("Internal error: Checker was not properly defined!") 
        slide_review_llm_requests: List = self.checker.get_all_requests() 
        error_information: str = self.checker.get_error_information() 
        slide_contents_str: str = str(json.dumps(slide_content))

        self.logger.debug(f'check: slide_review_llm_requests: {slide_review_llm_requests}')
        request_inputs: List = [{
            'reviewer': self.reviewer,
            'request_name': request['request_name'],
            'request_llm': request['request'],
            'temperature': request['temperature'] if 'temperature' in request else 0.1,
            'top_p': request['top_p'] if 'top_p' in request else 0.1,
            'post_request_name': request['post_request_name'] if 'post_request_name' in request else None,
            # Following two are necessary for multi threading
            'error_information': error_information,
            'slide_contents_str': slide_contents_str,
            'requires_format_description': '1' if requires_format_description else '0'
        }  for request in slide_review_llm_requests ]

        return self._prepare_and_send_requests(request_inputs)