from abc import abstractmethod, ABC
from typing import List
import json
from logging import Logger
from domain.ichecker import IChecker

class ContextWindowExceededError(Exception):
    pass

class AbstractLLMAccess(ABC):
    def __init__(self, logger: Logger, reviewer: str, model_name: str): 
        self.reviewer = reviewer
        self.logger = logger
        self.checker = None
        self.model_name = model_name # "llama3-70b"  # or use gpt-4o-mini, gpt-4o as per access requested

    def set_checker(self, checker: IChecker):
        self.checker = checker

    @abstractmethod
    def _prepare_and_send_requests(self, request_inputs: List) -> List:
        """
        """
    @abstractmethod
    def _send_request_plain(self, messages: List, request_name: str) -> str: 
        """
        """

    def check(self, slide_content: List) -> List:
        if self.checker is None:
            raise Exception("Internal error: Checker was not properly defined!") 
        slide_review_llm_requests: List = self.checker.get_all_requests() 
        error_information: str = self.checker.get_error_information() 
        slide_contents_str: str = str(json.dumps(slide_content))

        request_inputs: List = [{
            'reviewer': self.reviewer,
            'request_name': request['request_name'],
            'request_llm': request['request'],
            # Following two are necessary for multi threading
            'error_information': error_information,
            'slide_contents_str': slide_contents_str
        }  for request in slide_review_llm_requests ]

        return self._prepare_and_send_requests(request_inputs)