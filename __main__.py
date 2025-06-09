import argparse
import os
import sys
import logging
from functools import partial
from typing import List, Dict
from service.application_service import ApplicationService, DocumentType
from domain.llm_utils import LLMUtils


program_name = os.path.basename(sys.argv[0])
parser = argparse.ArgumentParser(prog=program_name)
csv_ = partial(str.split, sep=',')

reviewer_name: str = "Elon Musk"
from_document: str = ""
model_name: str = "llama3.3-70b"
to_document: str = None
context_path: str = None
create_summary_findings: bool = False

llm_utils = LLMUtils(["green", "purple"], 
                     os.getenv("PPT2LLM_REQUESTS_SLIDE_TEXT", default=""), 
                     os.getenv("PPT2LLM_REQUESTS_SLIDE_ARTISTIC", default=""), 
                     os.getenv("PPT2LLM_REQUESTS_DECK_TEXT", default=""),
                     os.getenv("PPT2LLM_REQUESTS_WORD", default=""),
                     os.getenv("PPT2LLM_REQUESTS_PRE_POST_REQUEST", default=""))
selected_artistic_slide_requests: List = [ idx for idx in range(len(llm_utils.get_all_slide_artistic_review_llm_requests())) ]
selected_text_slide_requests: List = [ idx for idx in range(len(llm_utils.get_all_slide_text_review_llm_requests())) ]
selected_deck_requests: List = [ idx for idx in range(len(llm_utils.get_all_deck_review_llm_requests())) ]
pre_post_requests: List = [ idx for idx in range(len(llm_utils.get_all_pre_post_llm_requests())) ]
selected_paragraphs_requests: List = [ idx for idx in range(len(llm_utils.get_all_word_review_llm_requests())) ]
split_request_per_paragraph_deepness: int = -1
context_length: int = 120000
pre_post_request_id: int = 0
only_slides = None
document_type: DocumentType = DocumentType.PPTX

parser.add_argument('--from_document', type=str, help='Specify the document to open')
parser.add_argument('--to_document', type=str, help='Specify the review document to create')
parser.add_argument('--model_name', type=str, help=f'Specify the name of the LLM model to use. Default is {model_name}')
parser.add_argument('--context_path', type=str, help='Path to a text file (whatever extension) where the contect of the document is described. If not orovided, headings will be used as context.')
parser.add_argument('--detailed_analysis', action="store_true", help='Select a detailed analysis or high level one')
parser.add_argument('--reviewer_name', type=int, help=f'Specify a reviewer name (Default is {reviewer_name}): Consider for example Jeff Bezos for management review.')
parser.add_argument('--debug', action="store_true", help='Set logging to debug')
parser.add_argument('--force_top_p',type=float, help=f'Increases diversity from various probable outputs in results.')  # Add argument to increase diversity from various probable outputs in results
parser.add_argument('--force_temperature', type=float, help=f'Higher temperature increases non sense and creativity while lower yields to focused and predictable results.')  # Add argument to increase non sense and creativity while lower yields to focused and predictable results
parser.add_argument('--simulate_calls_only', action="store_true", help=f'Do not perform the calls to LLM: used for debugging purpose.')
parser.add_argument('--pre_post_requests', type=int, help=f'Specify pre post requests to format the output from the following list: [[ {llm_utils.get_all_pre_post_llm_requests_and_ids_str()} ]], default is {pre_post_request_id}')
parser.add_argument('--context_length', type=int, help=f'Specify the context length acceptable from the part of source file (without including the number of tokens of the request), default is {context_length}')

#ppt_parser = parser.add_subparsers(title='PowerPoint analysis')
subparsers = parser.add_subparsers(dest='command')

ppt_parser = subparsers.add_parser('ppt', help='PowerPoint analysis')
ppt_parser.add_argument('--skip_slides', type=csv_, help='Specify slides to skip: 1,2-5,8: Cannot be used with only_slides')
ppt_parser.add_argument('--only_slides', type=csv_, help='Specify slides to keep: 1,2-5,8: Cannot be used with skip_slides')
ppt_parser.add_argument('--text_slide_requests', type=csv_, help=f'Specify slide requests to process: 1,3-5,7 from the following list: [[ {llm_utils.get_all_slide_text_requests_and_ids_str()} ]], default is {selected_text_slide_requests}')
ppt_parser.add_argument('--no_text_slide_requests',action="store_true", help=f'Skip text slide by slide check')
ppt_parser.add_argument('--artistic_slide_requests', type=csv_, help=f'Specify slide requests to process: 1,3-5,7 from the following list: [[ {llm_utils.get_all_slide_artistic_requests_and_ids_str()} ]], default is {selected_artistic_slide_requests}')
ppt_parser.add_argument('--no_artistic_slide_requests',action="store_true", help=f'Skip artistic slide by slide check')
ppt_parser.add_argument('--deck_requests', type=csv_, help=f'Specify deck requests to process: 1,3-5,7 from the following list: [[ {llm_utils.get_all_deck_requests_and_ids_str()} ]], default is {selected_deck_requests}')
ppt_parser.add_argument('--no_deck_requests',action="store_true", help=f'Skip deck check')

doc_parser = subparsers.add_parser('doc', help='Word analysis')
doc_parser.add_argument('--skip_paragraphs', type=csv_, help='Specify paragraphs to skip: 1,2.1,3: Cannot be used with only_paragraphs')
doc_parser.add_argument('--only_paragraphs', type=csv_, help='Specify paragraphs to keep: 2,3.4,5: Cannot be used with skip_paragraphs')
doc_parser.add_argument('--split_request_per_paragraph_deepness', type=int, help='Specify paragraphs deepness to use to split requests, per default, no split is done (document split happens only per context_length)')
doc_parser.add_argument('--paragraphs_requests', type=csv_, help=f'Specify slide requests to process: 1,3-5,7 from the following list: [[ {llm_utils.get_all_word_review_llm_requests_and_ids_str()} ]], default is {selected_paragraphs_requests}')

args = parser.parse_args()

logging_level = logging.INFO

if args.debug:
    logging_level = logging.DEBUG
if args.from_document:
    from_document = args.from_document
if args.model_name:
    model_name = args.model_name
if args.force_temperature:
    llm_utils.set_default_temperature(args.force_temperature)
if args.force_top_p:
    llm_utils.set_default_top_p(args.force_top_p)
if args.to_document:
    to_document = args.to_document
if args.context_path:
    context_path = args.context_path
if args.reviewer_name:
    reviewer_name = args.reviewer_name
if args.pre_post_requests:
    pre_post_request_id = args.pre_post_requests

elements_to_skip: List = []
elements_to_keep: List = []

if args.command == 'doc':
    document_type = DocumentType.DOCX
    if args.paragraphs_requests:
        selected_paragraphs_requests = [ int(element) for element in args.paragraphs_requests ]
    if args.skip_paragraphs:
        elements_to_skip = args.skip_paragraphs
    if args.only_paragraphs:
        elements_to_keep = args.only_paragraphs
    if args.split_request_per_paragraph_deepness:
        split_request_per_paragraph_deepness = args.split_request_per_paragraph_deepness
elif args.command == 'ppt' or document_type == DocumentType.PPTX:
    document_type = DocumentType.PPTX
    if args.text_slide_requests:
        selected_text_slide_requests = LLMUtils.get_list_parameters(args.text_slide_requests)
    if args.no_text_slide_requests:
        selected_text_slide_requests = []
    if args.artistic_slide_requests:
        selected_artistic_slide_requests = LLMUtils.get_list_parameters(args.artistic_slide_requests)
    if args.no_artistic_slide_requests:
        selected_artistic_slide_requests = []
    if args.deck_requests:
        selected_deck_requests = LLMUtils.get_list_parameters(args.deck_requests)
    if args.no_deck_requests:
        selected_deck_requests = []
    if args.skip_slides and args.only_slides:
        print("ERROR: Please either use option skip_slides or only_slides but not both!")
        sys.exit(0)

    if args.skip_slides:
        elements_to_skip = llm_utils.get_list_parameters(args.skip_slides)
    if args.only_slides:
        elements_to_keep = llm_utils.get_list_parameters(args.only_slides)

ApplicationService(from_document, to_document, elements_to_skip, elements_to_keep, args.detailed_analysis, \
                   reviewer_name, args.simulate_calls_only, logging_level, llm_utils, context_length,\
                   selected_text_slide_requests, selected_artistic_slide_requests, \
                   selected_deck_requests, selected_paragraphs_requests, split_request_per_paragraph_deepness,
                   model_name, context_path, pre_post_request_id, document_type)