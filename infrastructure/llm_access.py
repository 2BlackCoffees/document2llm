"""
@author Jean-Philippe Ulpiano
"""
from openai import OpenAI
from pprint import pformat
from typing import List, Dict
import time
import re
import os
import json
import sys
from domain.allm_access import AbstractLLMAccess, ContextWindowExceededError

class LLMAccess(AbstractLLMAccess):

    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL"),
        # base_url="https://api.openai.com/v1"
        # api_key=os.getenv("OPENAI_API_KEY") is default
    )

    def _get_request_llm_to_string(self, request_input: Dict):
        request_llm: str = ""
        if type(request_input["request_llm"]) is list:
            request_llm = " ".join(request_input["request_llm"])
        else:
            request_llm = request_input["request_llm"]

        self.logger.debug(f'type(request_input["request_llm"]) = {type(request_input["request_llm"])}): request_input["request_llm"] = {request_input["request_llm"]}')
        self.logger.debug(f'request_llm = {request_llm}')

        return request_llm
    
    def _create_message(self, llm_requests: List, reviewer: str, content: str):
        self.logger.debug(f"_create_message:content = {content}")
        llm_requests.insert(0, {"role": "system", "content": f'[{self.llm_utils.get_llm_reviewer_set(reviewer)}]'})
        if self.llm_utils.get_additional_context() is not None:
            llm_requests.append({"role": "user",   "content": f'[{self.llm_utils.get_additional_context()}]'})
        instructions: str = self.llm_utils.get_llm_instructions()
        if instructions is not None:
            llm_requests.append({"role": "user",   "content": f'[{instructions}]'})
        llm_requests.append({"role": "user",   "content": content})
        self.logger.debug(f"_create_message:request_list = {pformat(llm_requests, width=150)}")
        return llm_requests

    def _create_messages(self, request_inputs: List, content: str):
        llm_requests: List = []
        request_names: List = []
        avg_temperature: float = 0
        avg_top_p: float = 0
        self.logger.debug(f"content: {content}")
        if len(request_inputs) > 0:
            # Prepare request and add content of slide
            for request_input in request_inputs:
                llm_requests.append({
                                     "role": "user", \
                                     "content": self._get_request_llm_to_string(request_input)
                                     }
                                    )
                request_names.append(request_input["request_name"])
                avg_temperature += request_input['temperature'] if request_input['temperature'] is not None else 0
                avg_top_p += request_input['top_p'] if request_input['top_p'] is not None else 0
            llm_requests = self._create_message(llm_requests, request_inputs[0]['reviewer'], content)
            request_names.append(request_inputs[0]["request_name"])
            avg_temperature /= len(request_inputs)
            avg_top_p /= len(request_inputs)
        return llm_requests, request_names, avg_temperature, avg_top_p

# Checkout: https://stackoverflow.com/questions/78084538/openai-assistants-api-how-do-i-upload-a-file-and-use-it-as-a-knowledge-base
    def _send_request_plain(self, messages: List, request_name: str, temperature: float, top_p: float) -> str: 
        #pprint(self.slide_content)
        #pprint(request)
        return_message: str = None

        reformatted_request_messages: List = []

        for message in messages:
            reformatted_message: dict = {}
            for key, value in message.items():
                if isinstance(value, str):
                    value = value.replace('\\uf0e0', '')
                reformatted_message[key] = value
            reformatted_request_messages.append(reformatted_message)

        self.logger.debug(f'\nRequesting LLm with:\n{"-" * 20}\n  Request name {request_name} '+\
                         f'\n  request JSON Dumped:\n  {"-" * 20}\n{json.dumps(reformatted_request_messages, sort_keys=True, indent=2, separators=(",", ": "))}'+\
                         f'\n  request NON JSON Dumped:\n  {"-" * 24}:\n{reformatted_request_messages}')
        review = self.client.chat.completions.create(
            model=self.model_name,
            messages=reformatted_request_messages,
            temperature=temperature,
            top_p=top_p
        )

        return_message = re.sub(r'\'\s+.*refusal=.*,.*role=.*\)', '', re.sub(r'ChatCompletionMessage\(content=', '', str(review.choices[0].message.content.strip())))
        formatted_response = "\n".join([ "  " + message for message in return_message.split("\n")])
        self.logger.info(f'\nRequest:\n{"-" * 13}\n{pformat(reformatted_request_messages, width=150)}')
        self.logger.info(f'\nLLm response:\n{"-" * 13}\n{formatted_response}')

        return {
            'request_name': request_name,
            'response': return_message,
            'temperature': temperature,
            'top_p': top_p

        }

    def _send_request(self, messages: List, error_information: str, request_name: str, temperature: float, top_p: float) -> str:
        openai_response: bool = False
        sleep_time: int = 10
        response: Dict = {}

        while not openai_response:
            try:
                response = self._send_request_plain(messages, request_name, temperature, top_p)
                openai_response = True
            except Exception as err:                    
                self.logger.warning(f"{error_information}: {request_name}: Caught exception {err=}, {type(err)=}\nMessage: {pformat(messages, width=150)}")
                if "ContextWindowExceededError" in str(err):
                    self.logger.error(f"{request_name}: It seems your request is too big.")
                    raise ContextWindowExceededError(f"{request_name}: It seems your request is too big.")
                self.logger.warning(f"{request_name}: Backoff retry: Sleeping {sleep_time} seconds.")
                time.sleep(sleep_time)
                if sleep_time < 30:
                    sleep_time = sleep_time * 2
        return response
    
    
    def _prepare_and_send_requests(self, request_inputs: List) -> List:
        return_value: List = []
        slide_contents_str: str = request_inputs[0]['slide_contents_str'] if len(request_inputs) > 0 else None
        error_information: str = request_inputs[0]['error_information'] if len(request_inputs) > 0 else None

        llm_requests, request_names, avg_temperature, avg_top_p = self._create_messages(request_inputs, slide_contents_str)
        return_value.append(self._send_request(llm_requests, \
                                                error_information, \
                                                " & ".join(request_names),
                                                avg_temperature, avg_top_p))
        return return_value
    



