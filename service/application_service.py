import re
import os
import sys
from pathlib import Path
import logging
from typing import List
from domain.llm_utils import LLMUtils
from domain.icontent_out import IContentOut
from domain.allm_access import AbstractLLMAccess
from infrastructure.llm_access import LLMAccess
from infrastructure.llm_access_detailed import LLMAccessDetailed
from infrastructure.llm_access_simulate import LLMAccessSimulateCalls
from infrastructure.llm_access_detailed_simulate import LLMAccessDetailedSimulateCalls
from infrastructure.content_out import ContentOut
from domain.ppt2gpt import PPT2GPT

class ApplicationService:
    def __init__(self, document_path: str, to_document: str, slides_to_skip: List, slides_to_keep: List, detailed_analysis: bool, reviewer_name: str, \
                 simulate_calls_only: bool, logging_level: logging, llm_utils: LLMUtils, \
                 selected_text_slide_requests: List, selected_artistic_slide_requests: List, \
                 selected_deck_requests: List, model_name: str, context_path: str, consider_bullets_for_crlf: bool= True):

        program_name = os.path.basename(sys.argv[0])
        logger = logging.getLogger(f'loggername_{program_name}')

        logging.basicConfig(encoding='utf-8', level=logging_level)

        path = Path(document_path)
        if not path.is_file():
            logger.error(f'The file {document_path} does not seem to exist ({os.getcwd()}).')
            exit(1)

        if context_path is not None:
            path = Path(context_path)
            if path.is_file():
                logger.info(f"Opening external context related request file: {context_path}")
                with open(context_path) as f:
                    force_context_content:str = "\n".join(f.readlines())
                    llm_utils.set_additional_context(force_context_content)
                    logger.info(f"Using context provided in command line through filename {context_path}:\n{force_context_content}")
            else:
                logger.warning(f"File {context_path} could not be read.")
                
        information_user: List = []
        if slides_to_skip is not None and len(slides_to_skip) > 0:
            information_user.append(f"Slides to be skipped are: {slides_to_skip}")
        if slides_to_keep is not None and len(slides_to_keep) > 0:
            information_user.append(f"Slides to be kept are: {slides_to_keep}")
        separator: str = " \n  * "
        if len(selected_text_slide_requests) > 0:
            information_user.append(f"LLM text Requests to be applied on each slide are:{separator}{llm_utils.get_all_slide_text_requests_and_ids_str(selected_text_slide_requests, separator)}")
        if len(selected_artistic_slide_requests) > 0:
            information_user.append(f"LLM artistic Requests to be applied on each slide are:{separator}{llm_utils.get_all_slide_artistic_requests_and_ids_str(selected_artistic_slide_requests, separator)}")
        if len(selected_deck_requests) > 0:
            information_user.append(f"LLM test Requests to be applied on the whole deck are:{separator}{llm_utils.get_all_deck_requests_and_ids_str(selected_deck_requests, separator)}")

        if to_document is None:
            to_document = re.sub(r'\.[^\.]*$', '', str(document_path))
            if detailed_analysis:
                to_document += "-detailed"
            to_document += '.md'
        
        logging.info(f"Creating review document {to_document} from {document_path}.")
        task_name: str = "Detailed Review" if detailed_analysis else "Review"
        content_out = ContentOut(f"{task_name} Of Filename {document_path}", f"Please ensure you are reading all this information checking your ppt.", f"{to_document}")
        content_out.add_title(1, "Configuration")
        for information in information_user:
            logger.info(information)
            content_out.document(information)
            
        llm_access: AbstractLLMAccess = None
        if detailed_analysis:
            llm_access = LLMAccessDetailed(logger, reviewer_name, model_name, llm_utils) if not simulate_calls_only else LLMAccessDetailedSimulateCalls(logger, reviewer_name, model_name, llm_utils)
        else:
            llm_access = LLMAccess(logger, reviewer_name, model_name, llm_utils) if not simulate_calls_only else LLMAccessSimulateCalls(logger, reviewer_name, model_name, llm_utils)

        PPT2GPT(document_path, slides_to_skip, slides_to_keep, logger, content_out, llm_utils, selected_text_slide_requests, \
                selected_artistic_slide_requests, selected_deck_requests, llm_access, consider_bullets_for_crlf)
   