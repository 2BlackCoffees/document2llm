"""
@author Jean-Philippe Ulpiano
"""
from abc import ABC, abstractmethod
from typing import List
from domain.llm_utils import LLMUtils
from pprint import pprint

class IChecker(ABC):
    def __init__(self, llm_utils: LLMUtils, from_list: List, separator_information: str, error_information: str, additional_requests: List = []):
        self.llm_utils: LLMUtils = llm_utils
        self.from_list: List = from_list
        self.error_information: str = error_information
        self.separator_information: str = separator_information
        self.additional_requests: List = additional_requests

    @abstractmethod
    def get_all_requests(self) -> List:
        """
        """

    def get_error_information(self) -> str:
        return self.error_information
    
    def get_separator_information(self) -> str:
        return self.separator_information
    

class DeckChecker(IChecker):
    def get_all_requests(self) -> List:
        return self.llm_utils.get_all_deck_review_llm_requests(self.from_list) + self.additional_requests

class ArtisticSlideChecker(IChecker):
    def get_all_requests(self) -> List:
        return self.llm_utils.get_all_slide_artistic_review_llm_requests(self.from_list) + self.additional_requests

class TextSlideChecker(IChecker):
    def get_all_requests(self) -> List:
        return self.llm_utils.get_all_slide_text_review_llm_requests(self.from_list) + self.additional_requests

class WordChecker(IChecker):
    def get_all_requests(self) -> List:
        return self.llm_utils.get_all_word_review_llm_requests(self.from_list) + self.additional_requests

class PostProcessChecker(IChecker):
    def get_all_requests(self) -> List:
        return self.additional_requests + self.llm_utils.get_post_additional_requests()

