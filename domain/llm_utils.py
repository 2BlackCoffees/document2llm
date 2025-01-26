from typing import Dict, List
import json
from pptx.enum.dml import MSO_COLOR_TYPE, MSO_FILL
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pprint import pprint, pformat
from pathlib import Path
class LLMUtils:
    def __init__(self, color_palette: List, slide_text_filename: str, slide_artistic_filename: str, slide_deck_filename: str):
        color_palette.append("transparent")
        slide_text_external_requests: List = self.__read_json(slide_text_filename)
        slide_artistic_external_requests: List = self.__read_json(slide_artistic_filename)
        deck_text_external_requests : List = self.__read_json(slide_deck_filename)
        self.slide_artistic_content_review_llm_requests = [
            {'request_name': 'Artistic review', 
                'request': f"Consider how the various colors, shapes and size of fonts provide would need some improvement to provide a more harmonious slide."\
                f"Please consider that {' '.join(color_palette)} are our main colors."},
            {'request_name': 'Experts feedback checks', 
                'request': "Consider what the reviewer might say for the slide if they read it."\
                "Please provide concrete and valuable suggest improvements."},
            {'request_name': 'Slide audience check',
                'request': "Observe the slide from the perspective of a sceptic, supporter, and unfamiliar reader."\
                "Please concrete and valuable suggest improvements."},
            {'request_name': 'Slide weakness and counter points checks',
                'request': "Identify the weakest parts of the slide (e.g., logic, structure, distinctiveness, colors, ...)."\
                "Imagine what a harsh critic might say and provide concrete valuable improvement suggestions to address these concerns."\
                "Imagine we're in a debate. Your job is to argue in opposition. What are your top 3 counterpoints for the overall slide?"}
        ]
        self.slide_artistic_content_review_llm_requests.extend(slide_artistic_external_requests)

        self.slide_text_review_llm_requests = [
            {'request_name': 'Spell check and Clarity checks', 
                'request': 'Perform a detailed spell check to ensure no spelling errors exist. '\
                'Verify that all terms used are clear and concise for any reader.'\
                'Identify any sections or slides that may be confusing or unclear.'},
            {'request_name': 'Slide Redability checks',
                'request': "Read the slide out loud and suggest simplification if the text is hard to read or comprehend."},
            {'request_name': 'Slide take away checks', 
                'request': "Ensure the whole slide text has a clear, memorable takeaway."\
                "Please provide concrete and valuable suggestion improvements."\
                "If takeaway is missing, provide a suggested takeaway for each slide"},
            {'request_name': 'Experts feedback checks', 
                'request': "Consider what the reviewer might say for the slide if they read it."\
                "Please provide concrete and valuable suggest improvements."},
            {'request_name': 'Slide memorability check', 
                'request': "Summarize the main point of the slide in less than two sentences and provide the sentences, make sure they are memorable.Please concrete and valuable suggest improvements."\
                "Review the title and opening paragraph of each slide. Suggest improvements if they don't grab your attention."},
            {'request_name': 'Slide audience check',
                'request': "Read the slide from the perspective of a sceptic, supporter, and unfamiliar reader."\
                "Please concrete and valuable suggest improvements."},
            {'request_name': 'Slide weakness and counter points checks',
                'request': "Identify the weakest parts of the slide (e.g., logic, structure, distinctiveness)."\
                "Imagine what a harsh critic might say and provide concrete valuable improvement suggestions to address these concerns."\
                "Imagine we're in a debate. Your job is to argue in opposition. What are your top 3 counterpoints for the text?"}
        ]
        self.slide_text_review_llm_requests.extend(slide_text_external_requests)

        self.deck_review_llm_requests = [
            {'request_name': 'Flow check', 
                'request': "Please review the whole flow considering all slides. Please suggest reordering of slides if some slides are not in the right order."},
            {'request_name': 'Consistency check', 
                'request': "Please review the whole flow considering all slides. Please suggest missing slides if some slides are missing. Please provide concreate and detailed examples of the missing slides."},
            {'request_name': 'Clarity checks', 
                'request': 'Identify any sections or slides that may be confusing or unclear.'},
            {'request_name': 'Deck Redability checks',
                'request': "Read all the slides out loud and suggest simplification if the text or flow is hard to read or comprehend."},
            {'request_name': 'Deck take away checks', 
                'request': "Ensure the whole deck text has a clear, memorable takeaway."\
                "Please provide concrete and valuable suggestion improvements ensuring that the reader has a good understanding of the message conveyed by the dec."},
            {'request_name': 'Experts feedback checks', 
                'request': "Consider what the reviewer might say for the deck if they read it."\
                "Please provide concrete and valuable suggest improvements."},
            {'request_name': 'Deck memorability check', 
                'request': "Summarize the main point of the deck in less than 10 sentences and provide the sentences, make sure the sentences are memorable."\
                "Review the title and opening paragraph of each slide. Suggest improvements if they don't grab your attention or the flow is not optimal."},
            {'request_name': 'Deck audience check',
                'request': "Read the deck from the perspective of a sceptic, supporter, and unfamiliar reader."\
                "Please concrete and valuable suggest improvements."},
            {'request_name': 'Deck weakness and counter points checks',
                'request': "Identify the weakest parts of the deck (e.g., logic, structure, distinctiveness)."\
                "Imagine what a harsh critic might say and provide concrete valuable improvement suggestions to address these concerns."\
                "Imagine we're in a debate. Your job is to argue in opposition. What are your top 3 counterpoints for the deck?"}
        ]
        self.deck_review_llm_requests.extend(deck_text_external_requests)

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
    
    def get_all_deck_review_llm_requests(self, from_list: List = None):
        return self.__get_all_requests(self.deck_review_llm_requests, from_list)
    
    def __get_all_slide_requests_and_ids(self, request_list: List, from_list: List = None):
        all_requests: List = []
        for idx, llm_request in enumerate(request_list):
            if from_list is None or idx in from_list:
                all_requests.append({'idx': idx, 'llm_request': llm_request['request_name']})
        return all_requests    
    
    def get_all_artistic_slide_requests_and_ids(self, from_list: List = None):
        return self.__get_all_slide_requests_and_ids(self.slide_artistic_content_review_llm_requests, from_list)
    
    def get_all_text_slide_requests_and_ids(self, from_list: List = None):
        return self.__get_all_slide_requests_and_ids(self.slide_text_review_llm_requests, from_list)
    
    def get_all_deck_requests_and_ids(self, from_list: List = None):
        return self.__get_all_slide_requests_and_ids(self.deck_review_llm_requests, from_list)
    
    def get_all_slide_artistic_requests_and_ids_str(self, from_list: List = None, separator: str = " *** "):
        all_requests = self.get_all_artistic_slide_requests_and_ids(from_list)
        return separator.join([f"{req['idx']}: {req['llm_request']}" for req in all_requests])
    
    def get_all_slide_text_requests_and_ids_str(self, from_list: List = None, separator: str = " *** "):
        all_requests = self.get_all_text_slide_requests_and_ids(from_list)
        return separator.join([f"{req['idx']}: {req['llm_request']}" for req in all_requests])
    
    def get_all_deck_requests_and_ids_str(self, from_list: List = None, separator: str = " *** "):
        all_requests = self.get_all_deck_requests_and_ids(from_list)
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
    
    @staticmethod    
    def get_llm_instructions():
        return f"""[Consider the following json for text boxes or groups of shapes the json information represents shapes of a pptx slide, your analysis shall take into account the full text present in the slide that can be extracted from the provided JSON as follows (Please NEVER EVER mention this JSON in your response, mention you are analyzing a slide instead):
                                
                            "shape": {{
                                "slide_number": This is the slide number: many shapes per slide will be provided,
                                "rotation_degrees": rotation of the shape in degree,
                                "shape_fore_color": filled colour of the shape: can be a 3 bytes hexadecimal vale RRGGBB or a Powerpoint scheme name,
                                "line":{{
                                    "line_color": colour of the line of the shape: can be a 3 bytes hexadecimal vale RRGGBB or a Powerpoint scheme name,
                                    "is_dash_style": "Yes" if dash_style  else "No",
                                    "line_width_points": line thickness in points
                                }},
                                "position": {{
                                    "from_left": This is the x position of the shape from the left,
                                    "from_top": This is the y position of the shape from the top
                                }},
                                "size": {{
                                    "width": This is the width of the shape Expressed in English Metric Units (EMU),
                                    "height": This is the height of the shape Expressed in English Metric Units (EMU) 
                                }},
                                "text": This is the text contained in the shape: it will contain a newline character (“n”) separating each paragraph and a vertical-tab (“v”) character for each line break,
                                "font_details": {{
                                    "font_name": Name of the font,
                                    "text_color": Color of the text: can be a 3 bytes hexadecimal vale RRGGBB or a Powerpoint scheme name,
                                    "font_size": Size of the font in points,
                                    "text_impacted": Part of the text mentioned before having the specific font details: Can be an array of strings
                                }}
                                "type": This is the type of the shape,
                                "is_title": This says if the text is the title of the slide
                            }}
                         
                         And consider following json for tables:
                            "shape": {{
                                "slide_number": This is the slide number,
                                "position": {{
                                    "from_left": This is the x position of the shape from the left,
                                    "from_top": This is the y position of the shape from the top
                                }},
                                "size": {{
                                    "width": This is the width of the shape,
                                    "height": This is the height of the shape
                                }},
                                "table_size": {{
                                    "number_cols": Number of columns of the table,
                                    "number_rows": Number of rows for the table
                                }},
                                "table_cells": [ array composed of json objects: row: row number, col: column number, text: associated text],
                                "type": "table"
                                }} ]
                            """