"""
@author Jean-Philippe Ulpiano
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict
from domain.ichecker import IChecker, PostProcessChecker
from logging import Logger
from domain.icontent_out import IContentOut
from domain.allm_access import AbstractLLMAccess
from domain.llm_utils import LLMUtils

import traceback
class ADocumentToDatastructure(ABC):
    content_out: IContentOut = None
    logger: Logger = None
    llm_access: AbstractLLMAccess = None
    flush_on_exception: bool = True
    def __init__(self, logger: Logger, content_out: IContentOut, 
                 llm_access: AbstractLLMAccess, llm_utils: LLMUtils):
        self.content_out = content_out
        self.logger = logger
        self.llm_access = llm_access
        self.llm_utils = llm_utils

    @abstractmethod
    def _document_to_data_structure(self) -> List:
        """
        """

    @abstractmethod
    def _get_title_rank_title_str_as_tuple(self, data: any) -> Tuple:
        """
        """

    @abstractmethod
    def _get_checker_instance(self, data: any) -> any:
        """
        """

    @abstractmethod
    def _get_llm_parameters_requests_as_tuple(self, data: any) -> Tuple:
        """
        """

    @abstractmethod
    def _get_done_text(self, data: any) -> str:
        """
        """

    def __print_initial_request(self, response: Dict, print_title: bool, slide_info: str) -> List:

                if print_title: 
                    self.content_out.add_title(2, f"{response['request_name']} (temperature: {response['temperature']}, top_p: {response['top_p']})")
                else:
                    self.content_out.document(f"**{response['request_name']}** (temperature: {response['temperature']}, top_p: {response['top_p']})")
                self.content_out.document_response(slide_info, response['response'])        

    def __send_llm_requests_and_expand_output(self, content_to_check: List, print_title: bool, slide_info: str) -> None:
            
            result: List = self.llm_access.check(content_to_check)
            for response in result:
                self.__print_initial_request(response, print_title, slide_info)
                # if print_title: 
                #     self.content_out.add_title(2, f"{response['request_name']} (temperature: {response['temperature']}, top_p: {response['top_p']})")
                # else:
                #     self.content_out.document(f"**{response['request_name']}** (temperature: {response['temperature']}, top_p: {response['top_p']})")
                # self.content_out.document_response(slide_info, response['response'])
                post_request: str = self.llm_utils.get_post_additional_request()
                self.logger.info(f"post_request: {post_request}")
                if len(post_request) > 0:
                    #self.content_out.add_title(title_rank, title_str)
                    post_process_checker: IChecker = PostProcessChecker(self.llm_utils, None, f' (Post Process)', f' (Post Process)')
                    self.llm_access.set_checker(post_process_checker)
                    post_process_result: List = self.llm_access.check(response['response'])
                    for post_process_response in post_process_result:
                        self.__print_initial_request(post_process_response, print_title, 'Post process: ' + slide_info)
                   
    def __core_process(self) -> None:
        data_structure: List = self._document_to_data_structure()
        for index, data in enumerate(data_structure):
            self.logger.debug(f"Executing request : {index + 1} / {len(data_structure)}")
            
            title_rank, title_str = self._get_title_rank_title_str_as_tuple(data)
            self.logger.info(f"{' ' * (title_rank * 2)}{'=' * 20} Processing {title_str} >>> {'=' * 20}  >> ")
            self.content_out.add_title(title_rank, title_str)

            instance_checker: IChecker = self._get_checker_instance(data)
            if instance_checker is not None:
                self.llm_access.set_checker(instance_checker)
                self.__send_llm_requests_and_expand_output(*self._get_llm_parameters_requests_as_tuple(data))
            
            done_text: str = self._get_done_text(data)
            if done_text is not None:
                self.logger.info(f"{' ' * (title_rank * 2)}{'=' * 20} <<< Finished processing {done_text} done and documented {'=' * 20}")  

    def process(self) -> None:
        if self.flush_on_exception:
            try:
                self.__core_process()
            except Exception as err:                    
                self.logger.warning(f"Caught exception {err=}\n {type(err)=}\n {traceback.print_exc()}\n Leaving application.")
        else:
            self.__core_process()

        self.content_out.flush_and_close()
