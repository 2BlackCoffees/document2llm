"""
@author Jean-Philippe Ulpiano
"""
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
import xml.etree.ElementTree as ET
from xml.etree import ElementTree
from io import StringIO
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
    INIT_PARAGRAPH: str = '0.0.0.0'


    def __init__(self, document_path: str, paragraphs_to_skip: List, paragraphs_to_keep: List,\
                 logger: Logger, content_out: IContentOut, llm_utils: LLMUtils, \
                 selected_paragraphs_requests: List, split_request_per_paragraph_deepness: int, llm_access: AbstractLLMAccess, 
                 context_length_source_document: int, enable_ocr: bool):
        super().__init__(logger, content_out, llm_access)
        self.document =  Document(document_path)
        self.llm_utils = llm_utils
        self.document_path = document_path
        self.paragraphs_to_skip = self.__paragraph_number_string_list(paragraphs_to_skip)
        self.paragraphs_to_keep = self.__paragraph_number_string_list(paragraphs_to_keep)
        self.selected_paragraphs_requests = selected_paragraphs_requests
        self.context_length_source_document = context_length_source_document
        self.split_request_per_paragraph_deepness = split_request_per_paragraph_deepness
        self.enable_ocr = enable_ocr
        if self.enable_ocr: 
            import easyocr


    def __paragraph_number_string_list(self, paragraph_number_list: List) -> List:
        if paragraph_number_list is None: 
            return None
        return [ paragraph_number + '.' if re.match(r'^\d+$', paragraph_number) else paragraph_number for paragraph_number in paragraph_number_list ]
    
    def __get_heading_deepness(self, heading_style) -> int:
        regexp = re.compile(r'^heading\s+(?P<heading_deepness>\d+)')
        m = regexp.match(heading_style)
        if m:
            return int(m.group('heading_deepness')) - 1
        return -1

    def __get_number_tokens(self, string: str) -> int:
        # Currently using a very approximate approach where we consider 2 to 3 characters per token
        # Instead a tokenizer of HuggingFace or similar should be used instead
        return len(re.sub(r'\s+', '', string)) / 2.8
    
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
                        if not re.match("List\sParagraph",cblock.style.name):
                            if len(col_list_data) > 0:
                                cell_value += " ".join(col_list_data)                            
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

    def get_ocred_images(self, xmlstr, root, namespaces, document, block) -> List:
        images_ocred: List = []
        unique_id: int = 0
        for run in block.runs:

            if 'pic:pic' in xmlstr:
                for pic in root.findall('.//pic:pic', namespaces):
                    cNvPr_elem = pic.find("pic:nvPicPr/pic:cNvPr", namespaces)
                    name_attr = cNvPr_elem.get("name")
                    blip_elem = pic.find("pic:blipFill/a:blip", namespaces)
                    embed_attr = blip_elem.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                    image_name = f'Document_Imagefile/{name_attr}/{embed_attr}/{unique_id}'
                    document_part = document.part
                    image_part = document_part.related_parts[embed_attr]
                    self.logger.info(f"Extracting OCR for image {image_name} (In case of memory error deactivate OCR)")
                    reader = easyocr.Reader(['en', 'de', 'fr', 'da'])
                    ocred_text: str = reader.readtext(image_part._blob)
                    for text in ocred_text:
                        ocred_text += (f'OCRed text: {text}\n')
                    self.logger.info(f"OCRed for image {image_name}:\n{ocred_text}\n")
                    images_ocred.append((image_name, ocred_text))

                unique_id = unique_id + 1
        return images_ocred
            

    def _document_to_data_structure(self):
        text_for_request: str = ""
        last_text_found: str = ""
        latest_saved_heading_deepness: int = 0
        paragraphs_to_process: List = []
        paragraph_number:str = self.INIT_PARAGRAPH
        data_structure: List = []

        for doc_part in self.iter_all_docx_blocks(self.document):
            image_found: bool = False
            namespaces: List = None
            root = None
            if 'text' in str(doc_part):
                current_text_list: List = []
                for run in doc_part.runs:                        
                    if run.bold:
                        current_text_list.append(f'** {run.text} ** ')
                    else:
                        current_text_list.append(run.text)
                    if self.enable_ocr:
                        xmlstr: str = str(run.element.xml)
                        namespaces = dict([node for _, node in ElementTree.iterparse(StringIO(xmlstr), events=['start-ns'])])
                        root = ET.fromstring(xmlstr) 
                        image_found = True

                current_heading_style: str = doc_part.style.name.lower()
                if current_heading_style.startswith('heading'):
                    current_heading_deepness: int = self.__get_heading_deepness(current_heading_style)
                    paragraph_number = self.__increase_paragraph_number(paragraph_number, current_heading_deepness)
                    self.logger.info(f'paragraph_number: {paragraph_number}, self.paragraphs_to_skip: {self.paragraphs_to_skip}, self.paragraphs_to_keep: {self.paragraphs_to_keep}')
                    if (self.__paragraph_number_caught(paragraph_number, self.paragraphs_to_skip) == True):
                        self.logger.info(f"Paragraph {paragraph_number} being activeliy skipped as per request.")
                        continue

                    if (self.__paragraph_number_caught(paragraph_number, self.paragraphs_to_keep) == False):
                        self.logger.info(f"Paragraph {paragraph_number} being skipped because not expected to be kept as per request.")
                        continue

                    if self.__get_number_tokens(text_for_request + last_text_found) < self.context_length_source_document and \
                       current_heading_deepness > latest_saved_heading_deepness and \
                       self.split_request_per_paragraph_deepness - 1 != current_heading_deepness:
                        text_for_request += last_text_found
                        last_text_found = ""
                    else:
                        latest_saved_heading_deepness = current_heading_deepness
                        data_structure = self.__append_to_data_structure(data_structure, text_for_request, paragraphs_to_process, paragraph_number)
                        text_for_request = last_text_found
                        last_text_found = ""
                        paragraphs_to_process = []
                    paragraphs_to_process.append(paragraph_number)
                    last_text_found += f'{"#" * current_heading_deepness} {" ".join(current_text_list)}\n\n'
                    
                else:
                    last_text_found += " ".join(current_text_list) + "\n\n"
                
                if image_found:
                    for ocred_image_name, ocred_image_text in self.get_ocred_images(xmlstr, root, namespaces, self.document, doc_part):
                        last_text_found += f'Image text from OCR: "{ocred_image_text}"\n\n'
                        self.logger.info(f'Image name {ocred_image_name}, content: {ocred_image_text}')

                    
            elif isinstance(doc_part, Table):
                last_text_found += self.__convert_to_md_table(doc_part) + "\n"    

        text_for_request += last_text_found
        if len(text_for_request) > 0:
            data_structure = self.__append_to_data_structure(data_structure, text_for_request, paragraphs_to_process, paragraph_number)
        self.logger.info(f"Prepared document:\n{data_structure}")
        self.logger.info(f"Number requests :\n{len(data_structure)}")
        for data in data_structure:
            self.logger.info(f'{data[self.TITLE_PARAMS][1]}: {int(self.__get_number_tokens(data[self.LLM_REQUEST_PARAMS][0]) * 10000 / self.context_length_source_document)/100.0}% context length used')

        return data_structure
    
    def _get_title_rank_title_str_as_tuple(self, data: Dict) -> Tuple:
        return data[self.TITLE_PARAMS]

    def _get_checker_instance(self, data: Dict) -> any:
        return data[self.CHECKER_INSTANCE]

    def _get_llm_parameters_requests_as_tuple(self, data: any) -> Tuple:
        return data[self.LLM_REQUEST_PARAMS]
    
    def _get_done_text(self, data: any) -> str:
        return data[self.DONE_TEXT]