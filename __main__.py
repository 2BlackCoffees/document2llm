import argparse
import os
import sys
import logging
from functools import partial
from typing import List, Dict
from infrastructure.content_out import ContentOut
#from domain.ppt2gpt import PPT2GPT
from service.application_service import ApplicationService
from domain.llm_utils import LLMUtils

program_name = os.path.basename(sys.argv[0])
parser = argparse.ArgumentParser(prog=program_name)
csv_ = partial(str.split, sep=',')

reviewer_name: str = "Elon Musk"
from_document: str = ""
model_name: str = "llama3-70b"



llm_utils = LLMUtils(["green", "purple"], 
                     os.getenv("PPT2LLM_REQUESTS_SLIDE_TEXT", default=""), 
                     os.getenv("PPT2LLM_REQUESTS_SLIDE_ARTISTIC", default=""), 
                     os.getenv("PPT2LLM_REQUESTS_DECK_TEXT", default=""))
selected_artistic_slide_requests: List = [ idx for idx in range(len(llm_utils.get_all_slide_artistic_review_llm_requests())) ]
selected_text_slide_requests: List = [ idx for idx in range(len(llm_utils.get_all_slide_text_review_llm_requests())) ]
selected_deck_requests: List = [ idx for idx in range(len(llm_utils.get_all_deck_review_llm_requests())) ]
only_slides = None

parser.add_argument('--from_document', type=str, help='Specify the document to open')
parser.add_argument('--model_name', type=str, help=f'Specify the name of the LLM model to use. Default is {model_name}')
parser.add_argument('--skip_slides', type=csv_, help='Specify slides to skip: 1,2-5,8: Cannot be used with only_slides')
parser.add_argument('--only_slides', type=csv_, help='Specify slides to keep: 1,2-5,8: Cannot be used with skip_slides')
parser.add_argument('--text_slide_requests', type=csv_, help=f'Specify slide requests to process: 1,3-5,7 from the following list: [[ {llm_utils.get_all_slide_text_requests_and_ids_str()} ]], default is {selected_text_slide_requests}')
parser.add_argument('--no_text_slide_requests',action="store_true", help=f'Skip text slide by slide check')
parser.add_argument('--artistic_slide_requests', type=csv_, help=f'Specify slide requests to process: 1,3-5,7 from the following list: [[ {llm_utils.get_all_slide_artistic_requests_and_ids_str()} ]], default is {selected_artistic_slide_requests}')
parser.add_argument('--no_artistic_slide_requests',action="store_true", help=f'Skip artistic slide by slide check')
parser.add_argument('--deck_requests', type=csv_, help=f'Specify deck requests to process: 1,3-5,7 from the following list: [[ {llm_utils.get_all_deck_requests_and_ids_str()} ]], default is {selected_deck_requests}')
parser.add_argument('--no_deck_requests',action="store_true", help=f'Skip deck check')
parser.add_argument('--detailed_analysis', action="store_true", help='Select a detailed analysis or high level one')
parser.add_argument('--reviewer_name', type=int, help=f'Specify a reviewer name (Default is {reviewer_name}): Consider for example Jeff Bezos for management review.')
parser.add_argument('--debug', action="store_true", help='Set logging to debug')
parser.add_argument('--simulate_calls_only', action="store_true", help=f'Do not perform the calls to LLM: used for debugging purpose.')
args = parser.parse_args()

logging_level = logging.INFO

if args.debug:
    logging_level = logging.DEBUG
if args.text_slide_requests:
    selected_text_slide_requests = LLMUtils.get_list_parameters(args.slide_requests)
if args.no_text_slide_requests:
    selected_text_slide_requests = []
if args.artistic_slide_requests:
    selected_artistic_slide_requests = LLMUtils.get_list_parameters(args.slide_requests)
if args.no_artistic_slide_requests:
    selected_artistic_slide_requests = []
if args.deck_requests:
    selected_deck_requests = LLMUtils.get_list_parameters(args.deck_requests)
if args.no_deck_requests:
    selected_deck_requests = []
if args.from_document:
    from_document = args.from_document
if args.model_name:
    model_name = args.model_name

if args.reviewer_name:
    reviewer_name = args.reviewer_name

if args.skip_slides and args.only_slides:
    print("ERROR: Please either use option skip_slides or only_slides but not both!")
    sys.exit(0)

slides_to_skip: List = []
if args.skip_slides:
    slides_to_skip = llm_utils.get_list_parameters(args.skip_slides)
slides_to_keep: List = []
if args.only_slides:
    slides_to_keep = llm_utils.get_list_parameters(args.only_slides)

ApplicationService(from_document, slides_to_skip, slides_to_keep, args.detailed_analysis, reviewer_name, args.simulate_calls_only, logging_level,\
                   llm_utils, selected_text_slide_requests, selected_artistic_slide_requests, selected_deck_requests, model_name)