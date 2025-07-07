
"""
@author Jean-Philippe Ulpiano
"""
from typing import List, Dict
import os
from concurrent.futures import ThreadPoolExecutor
from infrastructure.llm_access import LLMAccess
from pprint import pformat

class LLMAccessDetailed(LLMAccess):
    def __send_request_thread(self, request_input: Dict) -> str:
        requires_format_description: bool = request_input['requires_format_description'] == '1'

        llm_requests: List = [{"role": "user", 
                               "content": self._get_request_llm_to_string(request_input)}]
        llm_requests = self._create_message(llm_requests, request_input['reviewer'], request_input['slide_contents_str'], requires_format_description) 
        return self._send_request(llm_requests, \
                                  request_input['error_information'], \
                                  request_input["request_name"],\
                                  request_input['temperature'], \
                                  request_input['top_p'], \
                                  request_input['post_request_name'])
    
    def _prepare_and_send_requests( self, request_inputs: List):
        return_value: List = []
        number_processed_requests: int = 0
        while number_processed_requests < len(request_inputs):
            responses: List = []
            nb_workers: str = os.getenv("DOC2LLM_REQUESTS_NB_WORKERS", default="1")
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