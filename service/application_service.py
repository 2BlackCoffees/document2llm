"""
@author Jean-Philippe Ulpiano
"""
import re
import os
import sys
from pathlib import Path
from typing import List
import logging
from domain.llm_utils import UtilsLogger, LLMUtils, DocumentType
from domain.allm_access import AbstractLLMAccess
from domain.adocument2datastructure import ADocumentToDatastructure
from infrastructure.powerpoint2datastructure import PowerPointToDataStructure
from infrastructure.word2datastructure import WordToDatastructure
from infrastructure.md2datastructure import MDToDatastructure
from infrastructure.llm_access import LLMAccess
from infrastructure.llm_access_detailed import LLMAccessDetailed
from infrastructure.llm_access_simulate import LLMAccessSimulateCalls
from infrastructure.llm_access_detailed_simulate import LLMAccessDetailedSimulateCalls
from infrastructure.content_out import ContentOut

class ApplicationService:
    logger: logging.Logger = UtilsLogger.get_logger(__name__)
    def __load_text_file(self, file_path: str) -> str:
        text_file_content:str = None
        if file_path is not None:
            path = Path(file_path)
            if path.is_file():
                ApplicationService.logger.info(f"Opening external context related request file: {file_path}")
                with open(file_path) as f:
                    text_file_content = "\n".join(f.readlines())
                    ApplicationService.logger.info(f"Text file {file_path} contains:\n{text_file_content}")
            else:
                ApplicationService.logger.error(f"File {file_path} could not be read.")
                sys.exit(1)
        return text_file_content
    
    def __init__(self, document_path: str, to_document: str, elements_to_skip: List, elements_to_keep: List, detailed_analysis: bool, reviewer_properties_path: str, \
                 simulate_calls_only: bool, llm_utils: LLMUtils, context_length: int, enable_ocr: bool,\
                 selected_text_slide_requests: List, selected_artistic_slide_requests: List, \
                 selected_deck_requests: List, selected_paragraphs_requests: List, split_request_per_paragraph_deepness: int,
                 model_name: str, context_path: str, post_request_ids: List, document_type: DocumentType, consider_bullets_for_crlf: bool= True):

        ApplicationService.logger = ApplicationService.logger
        create_summary_findings: bool = True # TODO: We might need to find a better way to enable / disable it
        llm_utils.set_post_additional_requests(post_request_ids)
        path = Path(document_path)
        if not path.is_file():
            ApplicationService.logger.error(f'The file {document_path} does not seem to exist ({os.getcwd()}).')
            exit(1)

        force_context_content:str = self.__load_text_file(context_path)
        if force_context_content is not None:
            llm_utils.set_additional_context(force_context_content)
        reviewer_properties: str = self.__load_text_file(reviewer_properties_path)
        if reviewer_properties is None: reviewer_properties = LLMUtils.get_default_reviewer_properties()
               
        information_user: List = []
        if to_document is None:
            to_document = re.sub(r'\.[^\.]*$', '', str(document_path))
            if detailed_analysis:
                to_document += "-detailed"
            to_document += '.md'
        
        ApplicationService.logger.info(f"Analyzing document: {document_path}, results will be stored in: {to_document}.")
        task_name: str = "Detailed Review" if detailed_analysis else "Review"
        content_out = ContentOut(f"{task_name} Of Filename {document_path}", f"Please ensure you are reading all this information checking your ppt.", f"{to_document}", ApplicationService.logger, create_summary_findings)
        content_out.add_title(1, "Configuration")
        for information in information_user:
            ApplicationService.logger.info(information)
            content_out.document(information)
            
        llm_access: AbstractLLMAccess = None
        if detailed_analysis:
            llm_access = LLMAccessDetailed(ApplicationService.logger, reviewer_properties, model_name, llm_utils) if not simulate_calls_only else LLMAccessDetailedSimulateCalls(ApplicationService.logger, reviewer_properties, model_name, llm_utils)
        else:
            llm_access = LLMAccess(ApplicationService.logger, reviewer_properties, model_name, llm_utils) if not simulate_calls_only else LLMAccessSimulateCalls(ApplicationService.logger, reviewer_properties, model_name, llm_utils)

        document_to_llm: ADocumentToDatastructure = None
        if document_type == DocumentType.ppt:
            if elements_to_skip is not None and len(elements_to_skip) > 0:
                information_user.append(f"Slides to be skipped are: {elements_to_skip}")
            if elements_to_keep is not None and len(elements_to_keep) > 0:
                information_user.append(f"Slides to be kept are: {elements_to_keep}")
            separator: str = " \n  * "
            if len(selected_text_slide_requests) > 0:
                information_user.append(f"LLM text Requests to be applied on each slide are:{separator}{llm_utils.get_all_slide_text_requests_and_ids_str(selected_text_slide_requests, separator)}")
            if len(selected_artistic_slide_requests) > 0:
                information_user.append(f"LLM artistic Requests to be applied on each slide are:{separator}{llm_utils.get_all_slide_artistic_requests_and_ids_str(selected_artistic_slide_requests, separator)}")
            if len(selected_deck_requests) > 0:
                information_user.append(f"LLM test Requests to be applied on the whole deck are:{separator}{llm_utils.get_all_deck_requests_and_ids_str(selected_deck_requests, separator)}")
            document_to_llm = PowerPointToDataStructure(document_path, elements_to_skip, elements_to_keep, ApplicationService.logger, content_out, llm_utils, selected_text_slide_requests, \
                selected_artistic_slide_requests, selected_deck_requests, llm_access, consider_bullets_for_crlf)
        elif document_type == DocumentType.doc:
            document_to_llm = WordToDatastructure(document_path, elements_to_skip, elements_to_keep,\
                 ApplicationService.logger, content_out, llm_utils, \
                 selected_paragraphs_requests, split_request_per_paragraph_deepness, llm_access,  context_length, enable_ocr)
        elif document_type == DocumentType.md:
            document_to_llm = MDToDatastructure(document_path, elements_to_skip, elements_to_keep,\
                 ApplicationService.logger, content_out, llm_utils, \
                 selected_paragraphs_requests, split_request_per_paragraph_deepness, llm_access,  context_length)

        document_to_llm.process()
        ApplicationService.logger.info(f"Analysis stored in {to_document}")
        
   