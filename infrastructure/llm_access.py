from openai import OpenAI
from pprint import pformat
from typing import List, Dict
import time
import re
import os
from domain.llm_utils import LLMUtils
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
    
    def _create_message(self, reviewer: str, content: str, request_name: str):

        return [{"role": "system", "content": f"As {reviewer}, I am assigned the task of thoroughly reviewing key slides, with the goal of creating a high-quality document that exceeds expectations. To achieve this, I will conduct an in-depth analysis of the provided JSON file, which has been exported from a PowerPoint presentation. Specifically, I will focus on scrutinizing the complete text associated with each shape that makes up the slide, as represented in the JSON data. By leveraging the JSON structure as metadata, I will gain a deeper understanding of the slide's geometry and layout. However, in my analysis and subsequent documentation, I will exclusively refer to the original presentation deck, maintaining a focus on the content and design of the slides, without referencing the underlying JSON source."},
                {"role": "user", "content": LLMUtils.get_llm_instructions()},
                {"role": "user", "content": content}], \
               request_name

    def _create_messages(self, request_inputs: List, content: str):
        llm_requests: List = []
        request_names: List = []
        avg_temperature: float = 0
        avg_top_p: float = 0
        if len(request_inputs) > 0:
            # Prepare request and add content of slide
            llm_requests, request_name = self._create_message(request_inputs[0]['reviewer'], content, request_inputs[0]["request_name"])
            request_names.append(request_name)
            for request_input in request_inputs:
                llm_requests.append({
                                     "role": "user", \
                                     "content": self._get_request_llm_to_string(request_input)
                                     }
                                    )
                request_names.append(request_input["request_name"])
                avg_temperature += request_input['temperature'] if request_input['temperature'] is not None else 0
                avg_top_p += request_input['top_p'] if request_input['top_p'] is not None else 0

            avg_temperature /= len(request_inputs)
            avg_top_p /= len(request_inputs)
        return llm_requests, request_names, avg_temperature, avg_top_p

# Checkout: https://stackoverflow.com/questions/78084538/openai-assistants-api-how-do-i-upload-a-file-and-use-it-as-a-knowledge-base
    def _send_request_plain(self, messages: List, request_name: str, temperature: float, top_p: float) -> str: 
        #pprint(self.slide_content)
        #pprint(request)
        return_message: str = None

        self.logger.info(f'Requesting {request_name}')
        review = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            top_p=top_p
        )

        return_message = re.sub(r'\'\s+.*refusal=.*,.*role=.*\)', '', re.sub(r'ChatCompletionMessage\(content=', '', str(review.choices[0].message.content.strip())))

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
                self.logger.warning(f"{error_information}: {request_name}: Caught exception {err=}, {type(err)=}\nMessage: {pformat(messages)}")
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
                                                " & ".join(request_names)),
                                                avg_temperature, avg_top_p)
        return return_value
    



