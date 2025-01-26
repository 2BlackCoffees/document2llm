from openai import OpenAI
from pprint import pformat
from typing import List, Dict
import time
import re
import os
import json
from logging import Logger
from concurrent.futures import ThreadPoolExecutor
from domain.llm_utils import LLMUtils
from domain.ichecker import IChecker

class ContextWindowExceededError(Exception):
    pass

class LLMAccess:

    def __init__(self, logger: Logger, detailed_analysis: bool, reviewer: str, simulate_calls_only: bool, \
                 checker: IChecker, model_name: str): 
        self.reviewer = reviewer
        self.logger = logger
        self.detailed_analysis = detailed_analysis
        self.simulate_calls_only = simulate_calls_only
        self.checker = checker
        self.model_name = model_name # "llama3-70b"  # or use gpt-4o-mini, gpt-4o as per access requested

        self.client = OpenAI(
            # base_url=os.getenv("OPENAI_BASE_URL"),
            base_url="https://api.openai.com/v1"
            # api_key=os.getenv("OPENAI_API_KEY") is default
        )

    def __get_request_llm_to_string(self, request_input: Dict):
        request_llm: str = ""
        if type(request_input["request_llm"]) is list:
            request_llm = " ".join(request_input["request_llm"])
        else:
            request_llm = request_input["request_llm"]

        self.logger.debug(f'type(request_input["request_llm"]) = {type(request_input["request_llm"])}): request_input["request_llm"] = {request_input["request_llm"]}')
        self.logger.debug(f'request_llm = {request_llm}')

        return request_llm
    
    def __create_message(self, reviewer: str, content: str, request_name: str):

        return [{"role": "system", "content": f"As {reviewer}, I am assigned the task of thoroughly reviewing key slides, with the goal of creating a high-quality document that exceeds expectations. To achieve this, I will conduct an in-depth analysis of the provided JSON file, which has been exported from a PowerPoint presentation. Specifically, I will focus on scrutinizing the complete text associated with each shape that makes up the slide, as represented in the JSON data. By leveraging the JSON structure as metadata, I will gain a deeper understanding of the slide's geometry and layout. However, in my analysis and subsequent documentation, I will exclusively refer to the original presentation deck, maintaining a focus on the content and design of the slides, without referencing the underlying JSON source."},
                {"role": "user", "content": LLMUtils.get_llm_instructions()},
                {"role": "user", "content": content}], \
               request_name

    def __create_messages(self, request_inputs: List, content: str):
        llm_requests: List = []
        request_names: List = []
        if len(request_inputs) > 0:
            # Prepare request and add content of slide
            llm_requests, request_name = self.__create_message(request_inputs[0]['reviewer'], content, request_inputs[0]["request_name"])
            request_names.append(request_name)
            for request_input in request_inputs:
                llm_requests.append({"role": "user", "content": self.__get_request_llm_to_string(request_input)})
                request_names.append(request_input["request_name"])

        return llm_requests, request_names

# Checkout: https://stackoverflow.com/questions/78084538/openai-assistants-api-how-do-i-upload-a-file-and-use-it-as-a-knowledge-base
    def __send_request_plain(self, messages: List, request_name: str) -> str: 
        #pprint(self.slide_content)
        #pprint(request)
        return_message: str = None

        if not self.simulate_calls_only:
            self.logger.info(f'Requesting {request_name}')
            review = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )

            return_message = re.sub(r'\'\s+.*refusal=.*,.*role=.*\)', '', re.sub(r'ChatCompletionMessage\(content=', '', str(review.choices[0].message.content.strip())))
        else:
            #return_message = f"# No calls perfomed\nOriginal request:\n```{pformat(messages)}```"
            return_message = f"# No calls perfomed\nOriginal request:\n{pformat(messages)}"

        return {
            'request_name': request_name,
            'response': return_message #"\n".join([ re.sub(r'^#', '####', message) for message in return_message.split('\\n')])
        }

    def __send_request(self, messages: List, error_information: str, request_name: str) -> str:
        openai_response: bool = False
        sleep_time: int = 10
        response: Dict = {}

        while not openai_response:
            try:
                response = self.__send_request_plain(messages, request_name)
                openai_response = True
            except Exception as err:                    
                self.logger.warning(f"{error_information}: {request_name}: Caught exception {err=}, {type(err)=}\nMessage: {pformat(messages)}")
                if "ContextWindowExceededError" in str(err):
                    self.logger.error(f"{request_name}: It seems your request is too big.")
                    raise ContextWindowExceededError(f"{request_name}: It seems your request is too big.")
                self.logger.warning(f"{request_name}: Backoff retry: Sleeping {sleep_time} seconds.")
                time.sleep(sleep_time)
                if sleep_time < 30:
                    sleep_time = sleep_time * 2
        return response
    
    def __send_request_thread(self, request_input: Dict) -> str:
        llm_requests, request_name = self.__create_message(request_input['reviewer'], request_input['slide_contents_str'], request_input["request_name"]) 
        llm_requests.append({"role": "user", "content": self.__get_request_llm_to_string(request_input)})
        return self.__send_request(llm_requests, request_input['error_information'], request_name)

    def check(self, slide_content: List):
        return_value: List = []
        slide_review_llm_requests: List = self.checker.get_all_requests() 
        error_information: str = self.checker.get_error_information() 
        slide_contents_str: str = str(json.dumps(slide_content))

        request_inputs: List = [{
            'reviewer': self.reviewer,
            'request_name': request['request_name'],
            'request_llm': request['request'],
            # Following two are necessary for multi threading
            'error_information': error_information,
            'slide_contents_str': slide_contents_str
        }  for request in slide_review_llm_requests ]

        if not self.detailed_analysis:
            llm_requests, request_names = self.__create_messages(request_inputs, slide_contents_str)
            return_value.append(self.__send_request(llm_requests, \
                                                    error_information, \
                                                    " & ".join(request_names)))
        else:
            number_processed_requests: int = 0
            while number_processed_requests < len(request_inputs):
                responses: List = []
                nb_workers: str = os.getenv("PPT2LLM_REQUESTS_NB_WORKERS", default="1")
                max_workers: int = max(int(nb_workers if nb_workers.isdigit() else "1"), 1)
                number_batch_requests: int = min(len(request_inputs) - number_processed_requests, max_workers)
                sub_request_inputs: List = request_inputs[number_processed_requests : number_processed_requests + number_batch_requests]
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    responses = list(executor.map(self.__send_request_thread, sub_request_inputs))

                for response in responses:
                    response["request_name"] += self.checker.get_separator_information() 
                    return_value.append(response)
                number_processed_requests += number_batch_requests

        return return_value

