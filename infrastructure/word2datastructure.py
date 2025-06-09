import re
from pprint import pprint, pformat
from logging import Logger
import re
from typing import List, Dict, Tuple
from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
from docx.enum.style import WD_STYLE_TYPE
import xml.etree.ElementTree as ET
from PIL import Image
import json
#import pytesseract
import io
import sys
from domain.ichecker import WordChecker
from domain.allm_access import AbstractLLMAccess
from domain.llm_utils import LLMUtils
from domain.icontent_out import IContentOut
from domain.adocument2datastructure import ADocumentToDatastructure

class WordToDatastructure(ADocumentToDatastructure):
    TITLE_PARAMS: str = 'title_document'
    CHECKER_INSTANCE: str = 'checker_params'
    LLM_REQUEST_PARAMS: str = 'llm_request_params'
    DONE_TEXT: str = 'done_text'

    def __init__(self, document_path: str, paragraphs_to_skip: List, paragraphs_to_keep: List,\
                 logger: Logger, content_out: IContentOut, llm_utils: LLMUtils, \
                 selected_paragraphs_requests: List, split_request_per_paragraph_deepness: int, llm_access: AbstractLLMAccess, 
                 context_length_source_document: int):
        super().__init__(logger, content_out, llm_access)
        self.document =  Document(document_path)
        self.llm_utils = llm_utils
        self.document_path = document_path
        self.paragraphs_to_skip = paragraphs_to_skip
        self.paragraphs_to_keep = paragraphs_to_keep
        self.selected_paragraphs_requests = selected_paragraphs_requests
        self.context_length_source_document = context_length_source_document
        self.split_request_per_paragraph_deepness = split_request_per_paragraph_deepness
#
    def __get_heading_deepness(self, heading_style) -> int:
        regexp = re.compile(r'^heading\s+(?P<heading_deepness>\d+)')
        m = regexp.match(heading_style)
        if m:
            return int(m.group('heading_deepness')) - 1
        return -1

    def __get_tokens(self, string: str) -> int:
        # Currently using a very approximate approach, a tokenizer of OpenAI or HuggingFace should be used instead
        return len(string.split()) / 4
    
    def __increase_paragraph_number(self, paragraph_number: str, heading_deepness: int) -> List:
        paragraph_number_list = paragraph_number.split('.')
        if heading_deepness < len(paragraph_number_list):
            paragraph_number_list[heading_deepness] = str(int(paragraph_number_list[heading_deepness]) + 1)
            for index in range(heading_deepness + 1, len(paragraph_number_list)):
                paragraph_number_list[index] = '0'
            return '.'.join(paragraph_number_list)
   
    def iter_all_docx_blocks(self, parent):
        if isinstance(parent, _Document):
            parent_elm = parent.element.body
        elif isinstance(parent, _Cell):
            parent_elm = parent._tc
        else:
            raise ValueError("something's not right")
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    def __convert_to_md_table(self, table): 
        md_table: str = ""
        first_row: bool = True
        for row in table.rows:
            current_row: str = ""
            for cell in row.cells:
                cell_value: str = ""
                # --- 
                cell_value = ""
                col_list_data = []
                for cblock in self.iter_all_docx_blocks(cell):
                    if isinstance(cblock, Paragraph):
                        col_list_data.append(cblock.text)
                        # if re.match("List\sParagraph",cblock.style.name):
                        #     col_list_data.append(table.text)
                        # else:
                        if not re.match("List\sParagraph",cblock.style.name):
                            images = self.get_image_text(cblock)
                            if len(col_list_data) > 0:
                                cell_value += " ".join(col_list_data)                            
                            if len(images) > 0:
                                cell_value = cell_value + images
                            else:
                                cell_value = cell_value + cblock.text
                    elif isinstance(cblock, Table):
                        cell_value += self.__convert_to_md_table(cblock)
                current_row += f"|{cell_value}"
            if len(current_row) > 0:
                md_table += "\n" + current_row + "|"
            if first_row:
                md_table = "\n" + "|" + (("-" * 3) + " | ") * (len(current_row.split('|')) - 1)
                first_row = False
        return md_table


    def get_image_text(self, paragraph):
        img_ids: List = []
        root = ET.fromstring(paragraph._p.xml)
        tag_namespaces: Dict = {
                'a':"http://schemas.openxmlformats.org/drawingml/2006/main", \
                'r':"http://schemas.openxmlformats.org/officeDocument/2006/relationships", \
                'wp':"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
        image_parent_parts = root.findall('.//wp:inline', tag_namespaces)
        for inline in image_parent_parts:
            images = inline.findall('.//a:blip', tag_namespaces)
            for img in images:     
                id = img.attrib['{{{0}}}embed'.format(tag_namespaces['r'])]
                img_ids.append(id)
        image_parent_parts = root.findall('.//wp:anchor',tag_namespaces)
        for inline in image_parent_parts:
            images2 = inline.findall('.//a:blip', tag_namespaces)
            for img2 in images2:     
                id = img2.attrib['{{{0}}}embed'.format(tag_namespaces['r'])]
                img_ids.append(id)
        response = ""
        if len(img_ids) > 0:
            for id in img_ids:
                image_part = self.document.part.related_parts[id]
                image_stream = io.BytesIO(image_part._blob) 
                img = Image.open(image_stream)
                format = img.format.lower()
                # if (format in ("jpeg" ,"png" ,"gif" ,"bmp" ,"tiff" ,"jpg")):
                #     img_text = pytesseract.image_to_string(img)
                #     response +=img_text
        return response

    def __append_to_data_structure(self, data_structure: List, text_for_request: str, paragraphs_to_process: List) -> List:
        paragraphs_to_process_str: str = ', '.join(paragraphs_to_process) if len(paragraphs_to_process) > 0 else '<No paragraphs found!>'
        
        data_structure.append(
            {
                self.TITLE_PARAMS: (2, f"Check of content for paragraphs {paragraphs_to_process_str}"),
                self.CHECKER_INSTANCE: WordChecker(self.llm_utils, self.selected_paragraphs_requests, f' (Paragraphs {paragraphs_to_process_str})', f' (Paragraphs {paragraphs_to_process_str})'),
                self.LLM_REQUEST_PARAMS: (text_for_request, True, f'List of paragraphs: {paragraphs_to_process_str}'),
                self.DONE_TEXT: f"Paragraphs {paragraphs_to_process_str}"
            }
        )

        return data_structure

    def _document_to_data_structure(self):
        text_for_request: str = ""
        last_text_found: str = ""
        latest_saved_heading_deepness: int = 0
        paragraphs_to_process: List = []
        paragraph_number:str = '0.0.0.0'
        data_structure: List = []


        for doc_part in self.iter_all_docx_blocks(self.document):
            if isinstance(doc_part, Paragraph):
                current_heading_style: str = doc_part.style.name.lower()
                if current_heading_style.startswith('heading'):
                    current_heading_deepness: int = self.__get_heading_deepness(current_heading_style)
                    paragraph_number = self.__increase_paragraph_number(paragraph_number, current_heading_deepness)

                    if self.__get_tokens(text_for_request + last_text_found) < self.context_length_source_document and \
                       current_heading_deepness > latest_saved_heading_deepness and \
                       self.split_request_per_paragraph_deepness - 1 != current_heading_deepness:
                        text_for_request += last_text_found
                        last_text_found = ""
                    else:
                        latest_saved_heading_deepness = current_heading_deepness
                        data_structure = self.__append_to_data_structure(data_structure, text_for_request, paragraphs_to_process)
                        text_for_request = last_text_found
                        last_text_found = ""
                        paragraphs_to_process = []
                    paragraphs_to_process.append(paragraph_number)
                    last_text_found += f'{"#" * current_heading_deepness} {doc_part.text}\n\n'
                    
                else:
                    last_text_found += doc_part.text + "\n\n"
            elif isinstance(doc_part, Table):
                last_text_found += self.__convert_to_md_table(doc_part) + "\n"    

        text_for_request += last_text_found
        if len(text_for_request) > 0:
            data_structure = self.__append_to_data_structure(data_structure, text_for_request, paragraphs_to_process)
        self.logger.info(f"Prepared document:\n{data_structure}")
        self.logger.info(f"Number requests :\n{len(data_structure)}")
        for data in data_structure:
            self.logger.info(f'{data[self.TITLE_PARAMS][1]}: {int(self.__get_tokens(data[self.LLM_REQUEST_PARAMS][0]) * 10000 / self.context_length_source_document)/100.0}% context length used')

        return data_structure
    
    def _get_title_rank_title_str_as_tuple(self, data: Dict) -> Tuple:
        return data[self.TITLE_PARAMS]

    def _get_checker_instance(self, data: Dict) -> any:
        return data[self.CHECKER_INSTANCE]

    def _get_llm_parameters_requests_as_tuple(self, data: any) -> Tuple:
        return data[self.LLM_REQUEST_PARAMS]
    
    def _get_done_text(self, data: any) -> str:
        return data[self.DONE_TEXT]