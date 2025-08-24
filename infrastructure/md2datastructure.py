"""
@author Jean-Philippe Ulpiano
"""



import re
from pprint import pprint, pformat
from logging import Logger
import re
from typing import List, Dict, Tuple
from pathlib import Path

from domain.ichecker import WordChecker
from domain.allm_access import AbstractLLMAccess
from domain.llm_utils import LLMUtils
from domain.icontent_out import IContentOut
from domain.adocument2datastructure import ADocumentToDatastructure

class MDToDatastructure(ADocumentToDatastructure):
    TITLE_PARAMS: str = 'title_document'
    CHECKER_INSTANCE: str = 'checker_params'
    LLM_REQUEST_PARAMS: str = 'llm_request_params'
    DONE_TEXT: str = 'done_text'
    INIT_PARAGRAPH: str = '0.0.0.0'

    def __init__(self, document_path: str, paragraphs_to_skip: List, paragraphs_to_keep: List,\
                 logger: Logger, content_out: IContentOut, llm_utils: LLMUtils, \
                 selected_paragraphs_requests: List, split_request_per_paragraph_deepness: int, llm_access: AbstractLLMAccess, 
                 context_length_source_document: int):
        super().__init__(logger, content_out, llm_access, llm_utils)
        self.document: List =  self.__read_text_file(document_path)
        self.document_path = document_path
        self.paragraphs_to_skip = self.__paragraph_number_string_list(paragraphs_to_skip)
        self.paragraphs_to_keep = self.__paragraph_number_string_list(paragraphs_to_keep)
        self.selected_paragraphs_requests = selected_paragraphs_requests
        self.context_length_source_document = context_length_source_document
        self.split_request_per_paragraph_deepness = split_request_per_paragraph_deepness

    def __read_content(self, file_handler, start_exclude_keywords: List, stop_exclude_key_words: List, filter_header_footers: bool = False) -> List:
        file_content: List = []
        start_exclude_keywords_reg_exp: List = [re.compile(elt) for elt in start_exclude_keywords]
        stop_exclude_key_words_reg_exp: List = [re.compile(elt) for elt in stop_exclude_key_words]
        file_content_excluded: bool = False
        while line := file_handler.readline():
            line = line.rstrip()
            if not file_content_excluded:
                if any(regex.search(line) for regex in start_exclude_keywords_reg_exp):
                    file_content_excluded = True
                    continue
            else:
                if any(regex.search(line) for regex in stop_exclude_key_words_reg_exp):
                    file_content_excluded = False
                    continue
            if (not filter_header_footers) or (not file_content_excluded):
                file_content.append(line)

        return file_content


    def __read_text_file(self, file_path: str, 
                         start_exclude_keywords: List = [r"^\s*<HEADER>", r"^\s*<FOOTER>"], 
                         stop_exclude_key_words: List = [r"^\s*</", r"^\s*<[A-Z_]*\/>", ]) -> List:
        text_file_content: List = None
        if file_path is not None:
            path = Path(file_path)
            if path.is_file():
                LLMUtils.logger.info(f"Opening file: {file_path}")
                try:
                    with open(file_path) as f:
                        text_file_content = self.__read_content(f, start_exclude_keywords, stop_exclude_key_words)
                except:
                    LLMUtils.logger.warning(f"Text file {file_path} could not be opened, trying with UTF-8")
                    try:
                        with open(file_path, encoding="utf8") as f:
                            text_file_content = self.__read_content(f, start_exclude_keywords, stop_exclude_key_words)
                    except:
                        LLMUtils.logger.warning(f"Text file {file_path} could not be opened in UTF-8, trying ignoring error: some content will be lost")
                        with open(file_path, errors='ignore') as f:
                            text_file_content = self.__read_content(f, start_exclude_keywords, stop_exclude_key_words)
                
                LLMUtils.logger.info(f"Text file {file_path} contains:\n{text_file_content[:100]}")
            else:
                LLMUtils.logger.error(f"File {file_path} could not be read.")
        return text_file_content
    
    def __paragraph_number_string_list(self, paragraph_number_list: List) -> List:
        if paragraph_number_list is None: 
            return None
        return [ paragraph_number + '.' if re.match(r'^\d+$', paragraph_number) else paragraph_number for paragraph_number in paragraph_number_list ]
    
    def __get_heading_deepness(self, line: str) -> int:
        regexp_heading = re.compile(r'^\s*(?P<heading_deepness>[#]+)[^#]+')
        m = regexp_heading.search(line)
        if m:
            return len(m.group('heading_deepness')) - 1
        return -1
   
    def __increase_paragraph_number(self, paragraph_number: str, heading_deepness: int) -> List:
        paragraph_number_list = paragraph_number.split('.')
        if heading_deepness < len(paragraph_number_list) and heading_deepness >= 0:
            paragraph_number_list[heading_deepness] = str(int(paragraph_number_list[heading_deepness]) + 1)
            for index in range(heading_deepness + 1, len(paragraph_number_list)):
                paragraph_number_list[index] = '0'
            return '.'.join(paragraph_number_list)
        return paragraph_number
   
    def __append_to_data_structure(self, data_structure: List, text_for_request: str, paragraphs_to_process: List, paragraph_number: str) -> List:
        paragraphs_to_process_str: str = '<No chapter found!>'
        if len(paragraphs_to_process) > 0:
            paragraphs_to_process_str: str = ', '.join(paragraphs_to_process) 
        elif paragraph_number == self.INIT_PARAGRAPH:
            '<Before first chapter!>'

        data_structure.append(
            {
                self.TITLE_PARAMS: (1, f"Check of content for chapters {paragraphs_to_process_str}"),
                self.CHECKER_INSTANCE: WordChecker(self.llm_utils, self.selected_paragraphs_requests, f' (Chapters {paragraphs_to_process_str})', f' (Chapters {paragraphs_to_process_str})'),
                self.LLM_REQUEST_PARAMS: (text_for_request, True, f'List of chapters: {paragraphs_to_process_str}'),
                self.DONE_TEXT: f"Chapters {paragraphs_to_process_str}"
            }
        )
        return data_structure

    def __paragraph_number_caught(self, paragraph_number: str, paragraph_number_list: List) -> bool:
        if paragraph_number_list is None or len(paragraph_number_list) == 0:
            return None
        if paragraph_number_list is not None and len(paragraph_number_list) > 0:
            for paragraph_start in paragraph_number_list:
                if paragraph_number.startswith(paragraph_start):
                    return True
        return False

    def _document_to_data_structure(self):
        text_for_request: str = ""
        last_text_found: str = ""
        latest_saved_heading_deepness: int = -1
        paragraphs_to_process: List = []
        paragraph_number:str = self.INIT_PARAGRAPH
        data_structure: List = []

        for line in self.document:
            self.logger.debug(f"Analyzing {line}")
            current_heading_deepness: int = self.__get_heading_deepness(line)
            if current_heading_deepness >= 0:
                paragraph_number = self.__increase_paragraph_number(paragraph_number, current_heading_deepness)
                self.logger.debug(f'paragraph_number: {paragraph_number}, self.paragraphs_to_skip: {self.paragraphs_to_skip}, self.paragraphs_to_keep: {self.paragraphs_to_keep}')
                if (self.__paragraph_number_caught(paragraph_number, self.paragraphs_to_skip) == True):
                    self.logger.info(f"Paragraph {paragraph_number} being actively skipped as per request.")
                    continue

                if (self.__paragraph_number_caught(paragraph_number, self.paragraphs_to_keep) == False):
                    self.logger.info(f"Paragraph {paragraph_number} being skipped because not expected to be kept as per request.")
                    continue

                if self.llm_utils.get_number_tokens(text_for_request + last_text_found) < self.context_length_source_document and \
                   current_heading_deepness > latest_saved_heading_deepness and \
                   current_heading_deepness > self.split_request_per_paragraph_deepness - 1:
                    text_for_request += last_text_found
                    last_text_found = ""
                elif len(text_for_request) > 0:
                        self.logger.debug(f"Preparing new request for text: {text_for_request}")
                        latest_saved_heading_deepness = current_heading_deepness
                        data_structure = self.__append_to_data_structure(data_structure, text_for_request, paragraphs_to_process, paragraph_number)
                        text_for_request = last_text_found
                        last_text_found = ""
                        paragraphs_to_process = []
                paragraphs_to_process.append(paragraph_number)
                last_text_found += line + '\n'
                
            else:
                last_text_found += line + '\n'
                
        text_for_request += last_text_found
        if len(text_for_request) > 0:
            data_structure = self.__append_to_data_structure(data_structure, text_for_request, paragraphs_to_process, paragraph_number)
        self.logger.debug(f"Prepared document:\n{data_structure}")
        self.logger.info(f"Number of requests to LLM:{len(data_structure)}")
        for data in data_structure:
            self.logger.info(f'{data[self.TITLE_PARAMS][1]}: {int(self.llm_utils.get_number_tokens(data[self.LLM_REQUEST_PARAMS][0]) * 10000 / self.context_length_source_document)/100.0}% context length used')

        return data_structure
    
    def _get_title_rank_title_str_as_tuple(self, data: Dict) -> Tuple:
        return data[self.TITLE_PARAMS]

    def _get_checker_instance(self, data: Dict) -> any:
        return data[self.CHECKER_INSTANCE]

    def _get_llm_parameters_requests_as_tuple(self, data: any) -> Tuple:
        return data[self.LLM_REQUEST_PARAMS]
    
    def _get_done_text(self, data: any) -> str:
        return data[self.DONE_TEXT]