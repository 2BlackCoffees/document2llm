"""
@author Jean-Philippe Ulpiano
"""
import re
from pprint import pprint, pformat
from logging import Logger
from typing import List, Dict, Tuple, Any
import pdfplumber
from domain.ichecker import WordChecker
from domain.allm_access import AbstractLLMAccess
from domain.llm_utils import LLMUtils
from domain.icontent_out import IContentOut
from domain.adocument2datastructure import ADocumentToDatastructure

class PDFToDatastructure(ADocumentToDatastructure):
    PIXELS_TOLERANCE: int = 2
    MAX_WORDS_IN_HEADING: int = 10
    MIN_SIZE_HEADING: float = 8.0  # minimum font size to consider for headings
    TITLE_PARAMS: str = 'title_document'
    CHECKER_INSTANCE: str = 'checker_params'
    LLM_REQUEST_PARAMS: str = 'llm_request_params'
    DONE_TEXT: str = 'done_text'
    INIT_PARAGRAPH: str = '0.0.0.0'

    def __init__(self, pdf_path: str, paragraphs_to_skip: List, paragraphs_to_keep: List,
                 logger: Logger, content_out: IContentOut, llm_utils: LLMUtils,
                 selected_paragraphs_requests: List, split_request_per_paragraph_deepness: int, llm_access: AbstractLLMAccess,
                 context_length_source_document: int):
        super().__init__(logger, content_out, llm_access, llm_utils)
        self.pdf_path = pdf_path
        self.paragraphs_to_skip = self.__paragraph_number_string_list(paragraphs_to_skip)
        self.paragraphs_to_keep = self.__paragraph_number_string_list(paragraphs_to_keep)
        self.selected_paragraphs_requests = selected_paragraphs_requests
        self.context_length_source_document = context_length_source_document
        self.split_request_per_paragraph_deepness = split_request_per_paragraph_deepness

    @staticmethod
    def __group_lines(words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group words into lines by their vertical 'top' coordinate.
        Words are assumed to be sorted left-to-right, top-to-bottom by pdfplumber.
        """
        lines = []
        current_line = []
        current_top = None

        for word in words:
            top = word.get("top")
            if current_top is None:
                current_top = top
                current_line = [word]
                lines.append(current_line)
                continue

            # If this word is on the same line (top within small tolerance), append
            if abs(top - current_top) <= PDFToDatastructure.PIXELS_TOLERANCE:  # tolerance in points; adjust if needed
                current_line.append(word)
            else:
                # start a new line
                current_line = [word]
                lines.append(current_line)
                current_top = top

        return lines

    @staticmethod
    def __line_text_and_metrics(line: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build the line text and extract metrics (max font size, bold-ish).
        """
        texts = [word.get("text", "") for word in line]
        full_text = "".join(texts)

        # Metrics
        sizes = [word.get("size", 0) for word in line]
        max_size = max(sizes) if sizes else 0
        avg_size = sum(sizes) / len(sizes) if sizes else 0

        # Bold-ish heuristic: fontname contains "Bold" (case-insensitive)
        bold_flags = [bool(re.search(r"bold", (word.get("fontname") or ""), re.I)) for word in line]
        is_bold = any(bold_flags)

        # Additional hints
        text_clean = full_text.strip()

        return {
            "text": text_clean,
            "max_size": max_size,
            "avg_size": avg_size,
            "is_bold": is_bold
        }

    @staticmethod
    def __is_heading(line_metrics: Dict[str, Any], mean_size: float, std_dev: float, min_size: float = 8.0) -> bool:
        """
        Decide if a line is a heading using:
        - very large font size compared to the page body (mean + k*std)
        - or explicit bold
        - and a reasonable minimum size
        """
        max_size = line_metrics["max_size"]
        is_large_enough = max_size >= min_size and (mean_size and max_size >= mean_size + 1.5 * std_dev)
        if line_metrics["is_bold"]:
            return True
        # Fallback: if size is notably large even if variance is small
        if is_large_enough:
            return True
        # Optional: uppercase and short line (common for headings)
        # t = line_metrics["text"].strip()
        # if t and t.isupper() and len(t.split()) <= PDFToDatastructure.MAX_WORDS_IN_HEADING:
        #     return True
        return False

    def _document_to_data_structure(self):
        """
        Return a list of headings with page number and approximate y-position.
        Each heading is a dict: { 'page': int, 'top': float, 'text': str }
        """
        text_for_request: str = ""
        last_text_found: str = ""
        latest_saved_heading_deepness: int = -1
        paragraphs_to_process: List = []
        paragraph_number: str = self.INIT_PARAGRAPH
        data_structure: List = []

        with pdfplumber.open(self.pdf_path) as pdf:
            for _, page in enumerate(pdf.pages, start=1):
                # extract words with their font info; tweak as needed
                words = page.extract_words(
                    x_tolerance=PDFToDatastructure.PIXELS_TOLERANCE,
                    y_tolerance=PDFToDatastructure.PIXELS_TOLERANCE,
                    keep_blank_chars=False,
                    use_text_flow=False  # rely on absolute positions
                )

                if not words:
                    continue

                # Sort words by vertical position then horizontal
                words_sorted = sorted(words, key=lambda w: (w.get("top", 0), w.get("x0", 0)))

                # Group into lines
                lines = PDFToDatastructure.__group_lines(words_sorted)

                # Compute page-level stats for headings
                line_metrics = [PDFToDatastructure.__line_text_and_metrics(line) for line in lines]

                # Compute mean and std of line sizes for this page
                sizes = [line_metric["max_size"] for line_metric in line_metrics if line_metric["max_size"] > 0]
                if sizes:
                    mean_size = sum(sizes) / len(sizes)
                    std_size = (sum((size - mean_size) ** 2 for size in sizes) / len(sizes)) ** 0.5
                else:
                    mean_size = 0
                    std_size = 0

                # Decide which lines are headings
                for _, line_metric in enumerate(line_metrics):
                    line_stripped = line_metric["text"].strip()
                    if not line_stripped:
                        continue
                    if PDFToDatastructure.__is_heading(line_metric, mean_size, std_size, min_size=PDFToDatastructure.MIN_SIZE_HEADING):
                        current_heading_deepness = line_stripped.count('.') + 1 if '.' in line_stripped else 1
                        paragraph_number = self.__increase_paragraph_number(paragraph_number, current_heading_deepness)
                        self.logger.debug(f'paragraph_number: {paragraph_number}, self.paragraphs_to_skip: {self.paragraphs_to_skip}, self.paragraphs_to_keep: {self.paragraphs_to_keep}')
                        if self.__paragraph_number_caught(paragraph_number, self.paragraphs_to_skip):
                            self.logger.info(f"Paragraph {paragraph_number} being actively skipped as per request.")
                            continue
                        if self.__paragraph_number_caught(paragraph_number, self.paragraphs_to_keep) == False:
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
                        last_text_found += f'{"#" * current_heading_deepness} {line_stripped}\n\n'
                    else:
                        last_text_found += line_stripped + "\n\n"


        text_for_request += last_text_found
        if len(text_for_request) > 0:
            data_structure = self.__append_to_data_structure(data_structure, text_for_request, paragraphs_to_process, paragraph_number)
        self.logger.debug(f"Prepared document:\n{data_structure}")
        self.logger.info(f"Number of requests to LLM:{len(data_structure)}")
        for data in data_structure:
            self.logger.info(f'{data[self.TITLE_PARAMS][1]}: {int(self.llm_utils.get_number_tokens(data[self.LLM_REQUEST_PARAMS][0]) * 10000 / self.context_length_source_document)/100.0}% context length used')

        return data_structure


    def __paragraph_number_string_list(self, paragraph_number_list: List) -> List:
        if paragraph_number_list is None:
            return None
        return [paragraph_number + '.' if re.match(r'^\d+$', paragraph_number) else paragraph_number for paragraph_number in paragraph_number_list]

    def __paragraph_number_caught(self, paragraph_number: str, paragraph_number_list: List) -> bool:
        if paragraph_number_list is None or len(paragraph_number_list) == 0:
            return None
        for paragraph_start in paragraph_number_list:
            if paragraph_number.startswith(paragraph_start):
                return True
        return False

    def __append_to_data_structure(self, data_structure: List, text_for_request: str, paragraphs_to_process: List, paragraph_number: str) -> List:
        paragraphs_to_process_str: str = '<No chapter found!>'
        if len(paragraphs_to_process) > 0:
            paragraphs_to_process_str = ', '.join(paragraphs_to_process)
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


    def __increase_paragraph_number(self, paragraph_number: str, heading_deepness: int) -> str:
        paragraph_number_list = paragraph_number.split('.')
        if heading_deepness < len(paragraph_number_list):
            paragraph_number_list[heading_deepness] = str(int(paragraph_number_list[heading_deepness]) + 1)
            for index in range(heading_deepness + 1, len(paragraph_number_list)):
                paragraph_number_list[index] = '0'
            return '.'.join(paragraph_number_list)
        return paragraph_number

    def _get_title_rank_title_str_as_tuple(self, data: Dict) -> Tuple:
        return data[self.TITLE_PARAMS]

    def _get_checker_instance(self, data: Dict) -> any:
        return data[self.CHECKER_INSTANCE]

    def _get_llm_parameters_requests_as_tuple(self, data: any) -> Tuple:
        return data[self.LLM_REQUEST_PARAMS]

    def _get_done_text(self, data: any) -> str:
        return data[self.DONE_TEXT]