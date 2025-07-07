"""
@author Jean-Philippe Ulpiano
"""
from typing import Dict, List
import json
import re
import os
from pprint import pprint, pformat
from pathlib import Path
from enum import Enum
import logging

class DocumentType(Enum):
    ppt = 1
    doc = 2

# TODO refactor with OOP: We need a word and a PPT specialisation
class LLMUtils:
    DOC2LLM_LOGGING_LEVEL: str = "DOC2LLM_LOGGING_LEVEL"
    post_additional_request_ids: List = []
    CREATE_SUMMARY_FINDINGS = "create_summary_findings"
    def __init__(self, color_palette: List, \
                 slide_text_filename: str, slide_artistic_filename: str, slide_deck_filename: str, word_requests_filename: str, additional_requests_filename: str):
        color_palette.append("transparent")
        slide_text_external_requests: List = self.__read_json(slide_text_filename)
        slide_artistic_external_requests: List = self.__read_json(slide_artistic_filename)
        deck_text_external_requests : List = self.__read_json(slide_deck_filename)
        word_review_external_requests: List = self.__read_json(word_requests_filename)
        additional_requests: List = self.__read_json(additional_requests_filename)
        self.document_type = DocumentType.ppt
        self.logger = LLMUtils.get_logger(__name__)

        self.additional_context: str = None
        self.slide_artistic_content_review_llm_requests = [
            {'request_name': 'Color artistic review', 
                'request': f"Consider how the various colors need some improvement to provide a more harmonious slide."\
                           f"Consider that {' '.join(color_palette)} are our main colors.",
                'temperature': 0.4, 'top_p': 0.4 
            },
            {'request_name': 'Size, position and shapes artistic review', 
                'request': f"Consider how the various size, position and type of the shapes need some improvement to provide a more harmonious slide.",
                'temperature': 0.4, 'top_p': 0.4 
            },
            {'request_name': 'Fonts and size artistic review', 
                'request': f"Consider how the various fonts, font color and the size of the text need some improvement to provide a more harmonious slide.",
                'temperature': 0.4, 'top_p': 0.4 
            },
            {'request_name': 'Global artistic check',
                'request': f"Consider how the various colour, size, position and type of the shapes together with the various fonts, font color and the size of the text need some improvement to provide a more harmonious slide. "\
                           f"Consider that {' '.join(color_palette)} are our main colors.",
                'temperature': 0.7, 'top_p': 0.6 
            }
        ]
        self.slide_artistic_content_review_llm_requests.extend(slide_artistic_external_requests)

        self.slide_text_review_llm_requests = [
            {'request_name': 'Spell check', 
                'request': 'Perform a detailed spell check to ensure no spelling errors exist: Verify all words and the grammatic in depth. ',
                'temperature': 0.3, 'top_p': 0.2 
            },
            {'request_name': 'Clarity check', 
                'request': 'Verify that all terms used are clear and concise for any reader.'\
                           'Identify any section that may be confusing or unclear, suggest improvements.',
                'temperature': 0.3, 'top_p': 0.2 
            },
            {'request_name': 'Slide Redability checks',
                'request': "Read the slide out loud and suggest simplification if the text is hard to read or comprehend.",
                'temperature': 0.3, 'top_p': 0.2 
            },
            {'request_name': 'Slide take away checks', 
                'request': "Ensure the whole slide text has a clear, memorable takeaway."\
                           "Please provide concrete and valuable suggestion improvements."\
                           "Ensure a takeaway exists and suggest improvement or propose one.",
                'temperature': 0.3, 'top_p': 0.2 
            }
        ]
        self.slide_text_review_llm_requests.extend(slide_text_external_requests)

        self.word_review_llm_requests = [
            {'request_name': 'Spell check', 
                'request': 'Perform a detailed spell check to ensure no spelling errors exist: Verify all words and the grammatic in depth. ',
                'temperature': 0.3, 'top_p': 0.2 
            },
            {'request_name': 'Clarity checks', 
                'request': 'Verify that all terms used are clear and concise for any reader.'\
                           'Identify any sections or paragraphs that may be confusing or unclear, suggest improvements.',
                'temperature': 0.3, 'top_p': 0.2 
            },
            {'request_name': 'Text Readability checks',
                'request': "Read all out loud and suggest simplification if the message is hard to read or comprehend.",
                'temperature': 0.3, 'top_p': 0.2 
            },
            {'request_name': 'Extract {DOC2LLM_DETAIL_TYPE, technical} details',
                'request': "* Extract all {DOC2LLM_DETAIL_TYPE, technical} details.\n \
                            * Provide {DOC2LLM_DETAIL_TYPE, technical} details as a list of bullet points.\n\
                            * Describe the complexity of the {DOC2LLM_DETAIL_TYPE, technical} expectation.\n\
                            * Prepare all necessary questions to ensure the {DOC2LLM_DETAIL_TYPE, technical} scope can be clarified.",
                'temperature': 0.3, 'top_p': 0.2 
            },
            {'request_name': 'Extract commercial details',
                'request': "* Extract all commercial details. \n\
                            * Provide all details regarding start date, end date and transition length if specified. \n\
                            * Provide commercial details as a list of bullet points. \n\
                            * Describe the complexity of the commercial expectations.\n\
                            * Prepare all necessary questions to ensure the commercial scope can be clarified.",
                'temperature': 0.3, 'top_p': 0.2 
            },
            {'request_name': 'Text take away checks', 
                'request': "Ensure all paragraphs have a clear, memorable takeaway."\
                           "Please provide concrete and valuable suggestion improvements."\
                           "Ensure a takeaway exists for each paragraph and suggest improvement or propose one new.",
                'temperature': 0.3, 'top_p': 0.2 
            }
        ]
        self.word_review_llm_requests.extend(word_review_external_requests)

        self.deck_review_llm_requests = [
            {'request_name': 'Flow check', 
                'request': "Review the whole flow considering all slides. Suggest reordering of slides and explain why your suggestion it if the slide order is not optimal.",
                'temperature': 0.3, 'top_p': 0.4 
            },
            {'request_name': 'Consistency check', 
                'request': "Review the whole flow considering all slides. If any slide is missing, provide concreate and detailed examples of the slides that need to be added.",
                'temperature': 0.3, 'top_p': 0.4 
            },
            {'request_name': 'Clarity checks', 
                'request': 'Identify any sections or slides that may be confusing or unclear.',
                'temperature': 0.3, 'top_p': 0.4 
            },
            {'request_name': 'Deck Redability checks',
                'request': "Read all the slides out loud and suggest simplification if the text or flow is hard to read or comprehend.",
                'temperature': 0.4, 'top_p': 0.4 
            },
            {'request_name': 'Deck take away checks', 
                'request': "Ensure the whole deck text has a clear, memorable takeaway."\
                           "Provide concrete and valuable suggestion improvements ensuring that the reader has a good understanding of the message conveyed by the deck.",
                'temperature': 0.4, 'top_p': 0.4 
            },
            {'request_name': 'Experts feedback checks', 
                'request': "Consider what the reviewer might say for the deck if they read it."\
                           "Provide concrete and valuable suggest improvements.",
                'temperature': 0.4, 'top_p': 0.4 
            },
            {'request_name': 'Deck memorability check', 
                'request': "Summarize the main point of the deck in less than 10 sentences and provide the sentences, make sure the sentences are memorable."\
                           "Review the title and opening paragraph of each slide. Suggest improvements if they don't grab your attention or the flow is not optimal.",
                'temperature': 0.4, 'top_p': 0.4 
            },
            {'request_name': 'Deck audience check',
                'request': "Read the deck from the perspective of a sceptic, supporter, and unfamiliar reader."\
                           "Provide concrete and valuable suggest improvements.",
                'temperature': 0.5, 'top_p': 0.6 
            },
            {'request_name': 'Deck weakness and counter points checks',
                'request': "Identify the weakest parts of the deck (e.g., logic, structure, distinctiveness)."\
                           "Imagine what a harsh critic might say and provide concrete valuable improvement suggestions to address these concerns."\
                           "Imagine we're in a debate. Your job is to argue in opposition. What are your top 3 counterpoints for the deck?",
                'temperature': 0.5, 'top_p': 0.6 
            },
            {'request_name': 'Roadmap',
                'request': "Describe the detailed technical roadmap for innovation that appears from the deck content. Propose suggestion for improvement assuming a harsh critic wanted to make it disruptive.",
                'temperature': 0.6, 'top_p': 0.6 
            },
        ]
        self.deck_review_llm_requests.extend(deck_text_external_requests)

        self.post_additional_requests = [
            {
                "request_name": "Summary finding", 
                "request": "- The below text is the result of a LLM analysis, provide 5 to 7 detailed findings including suggestions.\n\n- Follow this template: * **(Describe Finding Type)**: (Detail the finding). \n\n    * **(Suggestion Type)**): (As a numbered list: Provide 2 to 4 outstanding **CONCRETE** suggestions for improvement: Use ** the suggestion ** instead of _ The current finding _ ). - Summarize in a table the 10 most important finding types that you found: \n\n| Finding | Number | Weight |\n| --- | --- | --- |\n| (Finding Type: Not a summary but the type of finding) | (Number of such findings) | (Weight of this finding. It is an integer ranging between 0: Very superficial and has almost no impact to 10: Very important and must be corrected ASAP) |\n",
                'temperature': 0.6, 'top_p': 0.6, 
                self.CREATE_SUMMARY_FINDINGS: True
            },
            {
                "request_name": "Formatted output without summary", 
                "request": "- The below text is the result of a LLM analysis, provide all your findings including suggestions.\n\n- Follow this template: (* **Describe Finding Type**: Detail the finding). \n\n(    * **Suggestion Type**): (As a numbered list: Provide 2 to 4 outstanding **CONCRETE** suggestions for improvement: Use ** the suggestion ** instead of _ The current finding _ ).",
                'temperature': 0.6, 'top_p': 0.6, 
                self.CREATE_SUMMARY_FINDINGS: False

            }
        ]
        self.post_additional_requests.extend(additional_requests)
        self.process_update_env_vars()
    
    def process_update_env_vars(self) -> None:
        for request_group in [
                                self.word_review_llm_requests,
                                self.deck_review_llm_requests, 
                                self.slide_text_review_llm_requests, 
                                self.slide_artistic_content_review_llm_requests,
                                self.post_additional_requests
                             ]:
            for request in request_group:
                for request_type in ['request_name', 'request']:
                    request[request_type] = self.resolve_env_var(request[request_type])

    def resolve_env_var(self, request) -> str:
        list_replacements: List = []
        for match in re.finditer(r'{([^}]*)}', request, re.S):
            found_match = match.group(1)
            env_var_name: str = found_match
            default_value: str = ""
            if ',' in found_match:
                env_var_name, default_value = found_match.split(',')
            replacement: str = os.getenv(env_var_name, default_value)
            list_replacements.append((f'{{{found_match}}}', replacement))

        for match, replacement in list_replacements:
            request = request.replace(match, replacement, 1)
        return request

    def set_document_type(self, document_type: DocumentType) -> None:
        self.document_type = document_type

    def get_post_additional_requests_from_name(self, requested_post_request_name: List) -> List:
        post_requests_found: List = []
        for index, post_request in enumerate(self.post_additional_requests):
            existing_request_name = post_request['request_name']
            if existing_request_name == requested_post_request_name:
                # If the name exists multiple times, then it will be applied multiple times
                post_requests_found.append(post_request)
        return post_requests_found



    def get_post_additional_requests(self) -> List:
        return [ self.post_additional_requests[post_additional_request_id] \
                for post_additional_request_id in self.post_additional_request_ids \
                    if post_additional_request_id >= 0 and post_additional_request_id < len(self.post_additional_requests) ]
    
    def set_post_additional_requests(self, post_additional_request_ids: List) -> bool:
        self.post_additional_request_ids = post_additional_request_ids

        for post_additional_request_id in post_additional_request_ids:
            if post_additional_request_id >= 0 and post_additional_request_id < len(self.post_additional_requests):
                post_request: dict = self.post_additional_requests[post_additional_request_id]
                if self.CREATE_SUMMARY_FINDINGS in post_request: 
                    return post_request[self.CREATE_SUMMARY_FINDINGS]
            
        return False

    
    def set_additional_context(self, additional_context: str) -> None:
        self.additional_context = additional_context

    def get_additional_context(self) -> str:
        return self.additional_context
    
    def set_default_temperature_top_p_requests(self, list_requests: List, new_temperature: float, new_top_p: float) -> None:
        for request in list_requests:
            if new_temperature is not None:
                request['temperature'] = new_temperature
            if new_top_p is not None:
                request['top_p'] = new_top_p

    def set_default_temperature(self, new_temperature: float) -> None:
        """
        @brief Sets the temperature for all LLM requests.
        @param new_temperature The new temperature value.
        """
        self.set_default_temperature_top_p_requests(self.word_review_llm_requests, new_temperature, None)
        self.set_default_temperature_top_p_requests(self.slide_artistic_content_review_llm_requests, new_temperature, None)
        self.set_default_temperature_top_p_requests(self.slide_text_review_llm_requests, new_temperature, None)
        self.set_default_temperature_top_p_requests(self.deck_review_llm_requests, new_temperature, None)
        
    def set_default_top_p(self, new_top_p: float) -> None:
        """
        @brief Sets the top_p value for all LLM requests.
        @param new_top_p The new top_p value.
        """
        self.set_default_temperature_top_p_requests(self.word_review_llm_requests, None, new_top_p)
        self.set_default_temperature_top_p_requests(self.slide_artistic_content_review_llm_requests, None, new_top_p)
        self.set_default_temperature_top_p_requests(self.slide_text_review_llm_requests, None, new_top_p)
        self.set_default_temperature_top_p_requests(self.deck_review_llm_requests, None, new_top_p)

    def __read_json(self, filename: str):
        path = Path(filename)
        if path.is_file():
            with open(filename) as f:
                return json.load(f)
        return []

    def __get_all_requests(self, request_list: List, from_list: List = None):
        if from_list is None:
            return request_list
        else:
            return [ request_list[idx] for idx in from_list ]
    
    def get_all_slide_artistic_review_llm_requests(self, from_list: List = None):
        return self.__get_all_requests(self.slide_artistic_content_review_llm_requests, from_list)
    
    def get_all_slide_text_review_llm_requests(self, from_list: List = None):
        return self.__get_all_requests(self.slide_text_review_llm_requests, from_list)
    
    def get_all_word_review_llm_requests(self, from_list: List = None):
        return self.__get_all_requests(self.word_review_llm_requests, from_list)

    def get_all_deck_review_llm_requests(self, from_list: List = None):
        return self.__get_all_requests(self.deck_review_llm_requests, from_list)
    
    def get_all_post_llm_requests(self, from_list: List = None):
        return self.__get_all_requests(self.post_additional_requests, from_list)

    
    def __get_all_requests_and_ids(self, request_list: List, from_list: List = None):
        all_requests: List = []
        for idx, llm_request in enumerate(request_list):
            if from_list is None or idx in from_list:
                all_requests.append({'idx': idx, 'llm_request': llm_request['request_name']})
        return all_requests    
    
    def get_all_artistic_slide_requests_and_ids(self, from_list: List = None):
        return self.__get_all_requests_and_ids(self.slide_artistic_content_review_llm_requests, from_list)
    
    def get_all_word_review_llm_requests_and_ids(self, from_list: List = None):
        return self.__get_all_requests_and_ids(self.word_review_llm_requests, from_list)
    
    def get_all_text_slide_requests_and_ids(self, from_list: List = None):
        return self.__get_all_requests_and_ids(self.slide_text_review_llm_requests, from_list)
    
    def get_all_post_llm_requests_and_ids(self, from_list: List = None):
        return self.__get_all_requests_and_ids(self.post_additional_requests, from_list)
    
    def get_all_deck_requests_and_ids(self, from_list: List = None):
        return self.__get_all_requests_and_ids(self.deck_review_llm_requests, from_list)
    
    def get_all_deck_requests_and_ids(self, from_list: List = None):
        return self.__get_all_requests_and_ids(self.deck_review_llm_requests, from_list)
    
    def get_all_slide_text_requests_and_ids_str(self, from_list: List = None, separator: str = " *** "):
        all_requests = self.get_all_text_slide_requests_and_ids(from_list)
        return separator.join([f"{req['idx']}: {req['llm_request']}" for req in all_requests])
    
    def get_all_slide_artistic_requests_and_ids_str(self, from_list: List = None, separator: str = " *** "):
        all_requests = self.get_all_artistic_slide_requests_and_ids(from_list)
        return separator.join([f"{req['idx']}: {req['llm_request']}" for req in all_requests])
    
    def get_all_word_review_llm_requests_and_ids_str(self, from_list: List = None, separator: str = " *** "):
        all_requests = self.get_all_word_review_llm_requests_and_ids(from_list)
        return separator.join([f"{req['idx']}: {req['llm_request']}" for req in all_requests])
    
    def get_all_deck_requests_and_ids_str(self, from_list: List = None, separator: str = " *** "):
        all_requests = self.get_all_deck_requests_and_ids(from_list)
        return separator.join([f"{req['idx']}: {req['llm_request']}" for req in all_requests])

    def get_all_post_llm_requests_and_ids_str(self, from_list: List = None, separator: str = " *** "):
        all_requests = self.get_all_post_llm_requests_and_ids(from_list)
        return separator.join([f"{req['idx']}: {req['llm_request']}" for req in all_requests])
    
    @staticmethod
    def get_list_parameters(parameters):
        parameter_list: List = []
        for parameter in parameters:
            if '-' in parameter:
                parameter_range = parameter.split('-')
                for parameter_nb in range(int(parameter_range[0]), int(parameter_range[1]) + 1):
                    parameter_list.append(int(parameter_nb))
            else:
                parameter_list.append(int(parameter))
        return parameter_list
    
    def get_llm_reviewer_set(self, reviewer: str) -> str:
        return_str: str = f"- You impersonate {reviewer}, for all prompts keeping the characteristics leading to excellence as expected from {reviewer}\n"
        if self.document_type == DocumentType.ppt:
                return_str +=   "- The data you will analyze is an export of a deck into JSON data.\n"+\
                                "- Do not comment on the JSON source itself.\n"+\
                                "- The JSON structure will provide text content and shape's geometry and layout.\n"+\
                                "- In your analysis and  documentation, you will exclusively refer to the content of the JSON structure representing the document."
        return return_str

    # TODO: This method will have to be better integrated to provide graphic or table details according to the request 
    def get_format_description(self, request_has_graphical: bool = False):
        instructions: str = None
        if self.document_type == DocumentType.ppt:
            instructions = f"""Consider the following json for text boxes or groups of shapes the json information represents shapes of a pptx slide, your analysis shall take into account the full text present in the slide that can be extracted from the provided JSON as follows (Please NEVER EVER mention this JSON in your response, mention you are analyzing a slide instead):
                                    
                                "shape": {{
                                    "slide_number": This is the slide number: many shapes per slide will be provided,"""
            if request_has_graphical:
                instructions += """
                                    "rotation_degrees": rotation of the shape in degree,
                                    "shape_fore_color": filled colour of the shape: can be a 3 bytes hexadecimal vale RRGGBB or a Powerpoint scheme name,
                                    "line":{{
                                        "line_color": colour of the line of the shape: can be a 3 bytes hexadecimal vale RRGGBB or a Powerpoint scheme name,
                                        "is_dash_style": "Yes" if dash_style  else "No",
                                        "line_width_points": line thickness in points
                                    }},
                                    "position": {{
                                        "from_left": This is the x position of the shape from the left expressed in percentage of the width of the slide,
                                        "from_top": This is the y position of the shape from the top expressed in percentage of the height of the slide
                                    }},
                                    "size": {{
                                        "width": This is the width of the shape Expressed in percentage of the width of the slide,
                                        "height": This is the height of the shape Expressed  in percentage of the hgight of the slide
                                    }},
                                    "font_details": {{
                                        "font_name": Name of the font,
                                        "text_color": Color of the text: can be a 3 bytes hexadecimal vale RRGGBB or a Powerpoint scheme name,
                                        "font_size": Size of the font in points,
                                        "text_impacted": Part of the text mentioned before having the specific font details: Can be an array of strings
                                    }}
                """
                instructions += """
                                    "text": This is the text contained in the shape: it will contain a newline character (“n”) separating each paragraph and a vertical-tab (“v”) character for each line break,
                                    "type": This is the type of the shape,
                                    "is_title": This says if the text is the title of the slide
                                }}
                            
                            And consider following json for tables:
                                "shape": {{
                                    "slide_number": This is the slide number,"""
            if request_has_graphical:
                instructions += """
                                    "position": {{
                                        "from_left": This is the x position of the shape from the left expressed in percentage of the width of the slide,
                                        "from_top": This is the y position of the shape from the top expressed in percentage of the height of the slide
                                    }},
                                    "size": {{
                                        "width": This is the width of the shape expressed in percentage of the width of the slide,
                                        "height": This is the height of the shape expressed in percentage of the height of the slide
                                    }},
                                    "table_size": {{
                                        "number_cols": Number of columns of the table,
                                        "number_rows": Number of rows for the table
                                    }},"""
            instructions += """

                                    "table_cells": The table will be provided in a mark down format,
                                    "type": "table"
                                    }} 
                                """

            instructions = instructions.replace('\\"', '"').replace('\\n', '\n')
        return instructions

    @staticmethod
    def is_paragraph(md_text: str, paragraph_start_min_word_length: str = 3, paragraph_start_min_word_numbers: str = 1) -> bool:
        text:str = md_text.replace('**', '')
        minwords: int = int(paragraph_start_min_word_numbers)  
        regexp: str = f'(\\w{{{paragraph_start_min_word_length},}}\\b\\s+){{{minwords},}}\w{{{paragraph_start_min_word_length},}}\\b'
        paragraph_found: bool = (re.search(regexp, text) is not None)
        return paragraph_found
    
    @staticmethod
    def get_logger(logger_name: str) -> logging.Logger:
        logging_level: str = os.getenv(LLMUtils.DOC2LLM_LOGGING_LEVEL, default=logging.INFO)
        logger: logging.Logger = logging.getLogger(logger_name)
        logging.basicConfig(encoding='utf-8', level=logging_level)
        return logger

    @staticmethod
    def get_default_reviewer_properties() -> str:
        return "a SME able to first compose highly cost effective team and second is capable to setup very high quality focused teams" 
