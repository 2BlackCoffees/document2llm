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
    
    def _create_message(self, llm_requests: List, reviewer: str, content: str, requires_format_description: bool):
        self.logger.debug(f"_create_message:content = {content}")
        llm_requests.insert(0, {"role": "system", "content": f'[{self.llm_utils.get_llm_reviewer_set(reviewer)}]'})
        instructions: str = ""
        if self.llm_utils.get_additional_context() is not None:
            instructions += f'[{self.llm_utils.get_additional_context()}]\n'
        if requires_format_description:
            tmp_instructions: str = self.llm_utils.get_format_description()
            if tmp_instructions is not None:
                instructions += tmp_instructions + "\n"
        instructions += content + "\n"
        llm_requests.append({"role": "user",   "content": instructions})
        self.logger.debug(f"_create_message:request_list = {pformat(llm_requests, width=150)}")
        return llm_requests

    def _create_messages(self, request_inputs: List, content: str, requires_format_description: bool):
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
            llm_requests = self._create_message(llm_requests, request_inputs[0]['reviewer'], content, requires_format_description)
            request_names.append(request_inputs[0]["request_name"])
            avg_temperature /= len(request_inputs)
            avg_top_p /= len(request_inputs)
        return llm_requests, request_names, avg_temperature, avg_top_p

    # TODO: Actually this process should be ahndeled when appending messages not before sending them to the LLM
    def _reformat_messages(self, messages: List) -> List:
        role_key: str = 'role'
        system_value: str = 'system'
        previous_role_name: str = None
        optimized_messages: List = []
        # First ensure all system messages are properly clubbed together into 1 message only
        index_systems: List = []
        self.logger.debug(f"**** Before changes: \n{pformat(messages, width=250)}")
        for index, message in enumerate(messages):
            if role_key in message and message[role_key] == system_value:
                index_systems.append(index)
                self.logger.debug(f"Found system role at index {index}: {pformat(message, width=250)}")
        if len(index_systems) > 0:
            system_element: Dict = messages.pop(index_systems[0])
            messages.insert(0, system_element)
            if len(index_systems) > 1:
                system_element = messages[0]
                for index_to_move in index_systems[1:]:
                    additional_system_element = messages.pop(index_to_move)
                    for key, value in additional_system_element.items():
                        if key == role_key: continue
                        if key in system_element:
                            self.log.info(f"Extending {system_element[key]}\nwith\n{value}")
                            system_element[key] += '\n' + value
        
        self.logger.debug(f"**** Merged system roles to the begining: \n{pformat(messages, width=250)}")
                    
        # Now club messages together which are following each other and have the same role
        for index, message in enumerate(messages):
            if role_key in message:
                if message[role_key] == previous_role_name:
                    for key, value in message.items():
                        last_message: Dict = optimized_messages[-1]
                        if key != role_key:
                            if key in last_message: last_message[key] += '\n' + message[key]
                            else: last_message[key] = message[key]
                else:
                    previous_role_name = message[role_key]
                    optimized_messages.append(message)
            else:
                self.logger.error(f"Message {pformat(message)} does snot have any role {role_key}!")

        self.logger.debug(f"Merged all same roles together: {pformat(optimized_messages, width=250)}")
        # Clean content of messages
        reformatted_request_messages: List = []
        for message in optimized_messages:
            reformatted_message: dict = {}
            for key, value in message.items():
                if isinstance(value, str):
                    # TODO, use https://pypi.org/project/Unidecode/ instead
                    value = value.replace(r"\\u2019", "'").replace(r'\\u[\da-f]{4}', ' ')
                reformatted_message[key] = value
            reformatted_request_messages.append(reformatted_message)
        self.logger.debug(f"**** Removed string problems:\ndebug{pformat(reformatted_request_messages, width=250)}")

        return reformatted_request_messages
# Checkout: https://stackoverflow.com/questions/78084538/openai-assistants-api-how-do-i-upload-a-file-and-use-it-as-a-knowledge-base
    def _send_request_plain(self, messages: List, request_name: str, temperature: float, top_p: float, post_request_name: str) -> str: 
        #pprint(self.slide_content)
        #pprint(request)
        return_message: str = None

        self.logger.debug(f'\nRequesting LLm with:\n{"-" * 20}\n  Model: {self.model_name},  Request name {request_name} '+\
                         f'\n  request JSON Dumped:\n  {"-" * 20}\n{json.dumps(messages, sort_keys=True, indent=2, separators=(",", ": "))}'+\
                         f'\n  request NON JSON Dumped:\n  {"-" * 24}:\n{messages}')
        review = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            top_p=top_p
        )

        return_message = re.sub(r'\'\s+.*refusal=.*,.*role=.*\)', '', re.sub(r'ChatCompletionMessage\(content=', '', str(review.choices[0].message.content.strip())))
        formatted_response = "\n".join([ "  " + message for message in return_message.split("\n")])
        self.logger.info(f'\nRequest:\n{"-" * 13}\n{pformat(messages, width=250)}')
        self.logger.info(f'\nLLm response:\n{"-" * 13}\n{formatted_response}')

        return {
            'request_name': request_name,
            'response': return_message,
            'temperature': temperature,
            'top_p': top_p,
            'post_request_name': post_request_name
        }

    def _send_request(self, messages: List, error_information: str, request_name: str, temperature: float, top_p: float, post_request_name: str) -> str:
        openai_response: bool = False
        sleep_time: int = 10
        response: Dict = {}

        while not openai_response:
            try:
                reformatted_request_messages: List = self._reformat_messages(messages)
                response = self._send_request_plain(reformatted_request_messages, request_name, temperature, top_p, post_request_name)
                openai_response = True
            except Exception as err:                    
                self.logger.warning(f"{error_information}: {request_name}: Caught exception {err=}, {type(err)=}\nMessage: {pformat(reformatted_request_messages, width=150)}")
                if "ContextWindowExceededError" in str(err) or "openai.InternalServerError" in str(err):
                    self.logger.error(f"{request_name}: It seems your request is too big or an internal error occured.")
                    raise ContextWindowExceededError(f"{request_name}: It seems your request is too big or an internal error occured.")
                self.logger.warning(f"{request_name}: Backoff retry: Sleeping {sleep_time} seconds.")
                time.sleep(sleep_time)
                if sleep_time < 30:
                    sleep_time = sleep_time * 2
        return response
    
    
    def _prepare_and_send_requests(self, request_inputs: List) -> List:
        return_value: List = []
        slide_contents_str: str = request_inputs[0]['slide_contents_str'] if len(request_inputs) > 0 else None
        error_information: str = request_inputs[0]['error_information'] if len(request_inputs) > 0 else None
        post_request_name: str = request_inputs[0]['post_request_name'] if len(request_inputs) > 0 else None
        requires_format_description: bool = request_inputs[0]['requires_format_description'] == '1' if len(request_inputs) > 0 else None

        llm_requests, request_names, avg_temperature, avg_top_p = self._create_messages(request_inputs, slide_contents_str, requires_format_description)
        return_value.append(self._send_request(llm_requests, \
                                                error_information, \
                                                " & ".join(request_names),
                                                avg_temperature, avg_top_p,
                                                post_request_name))
        return return_value
    



