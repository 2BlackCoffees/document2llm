## Introduction
The `document2llm` script is a powerful tool designed to extract information and perform analysis on Word and PowerPoint documents using Large Language Models (LLMs). The script is highly configurable and can be extended to accommodate custom requests.

Table of Contents
=================
- [Table of Contents](#table-of-contents)
  - [Important Security Consideration](#important-security-consideration)
  - [Document Processing Approaches](#document-processing-approaches)
  - [Error Handling](#error-handling)
  - [Prerequisites](#prerequisites)
  - [Usage](#usage)
    - [Options](#options)
    - [PowerPoint Analysis](#powerpoint-analysis)
    - [Word Document Analysis](#word-document-analysis)
  - [LLM Requests](#llm-requests)
    - [LLM text Requests to be applied on each slide](#llm-text-requests-to-be-applied-on-each-slide)
    - [LLM artistic Requests to be applied on each slide](#llm-artistic-requests-to-be-applied-on-each-slide)
    - [LLM test Requests to be applied on the whole deck](#llm-test-requests-to-be-applied-on-the-whole-deck)
    - [LLM test Requests to be applied on word documents](#llm-test-requests-to-be-applied-on-word-documents)
  - [Script Extensibility](#script-extensibility)
    - [Environment Variables](#environment-variables)
    - [Creating your own request](#creating-your-own-request)
    - [Creating parametrizable requests](#creating-parametrizable-requests)
  - [Example Use Cases](#example-use-cases)
  - [LLM Model](#llm-model)
  - [Improvements](#improvements)
  - [Troubleshooting](#troubleshooting)

## Important Security Consideration
Please note that if you are analyzing confidential documents, the script must be used with an LLM endpoint that ensures the privacy and security of your requests.

## Document Processing Approaches
The program offers multiple review approaches, including:
* **Slide-by-Slide PowerPoint text Processing**: Analyzes the text content of each slide individually.
* **Artistic Colours and Disposition PowerPoint Processing**: (WIP) Evaluates the use of colors and layout, taking into account personal preferences and divergences.
* **Flow and Content PowerPoint Processing**: Examines the overall flow and content of the entire presentation.
* **Word document processing in whole or by chapter**: Examines word documents.

## Error Handling
The program incorporates a backoff retry mechanism out of the box. However, if the number of tokens exceeds the limit, the script will stop executing. 
Currently, for power point presentations, if you exceed the context length, the only solution is to split the presentation into smaller parts. 
In word documents instead, the context length is implemented leveraging a trivial token number processing approach.

## Prerequisites
Create a virtual environment (https://www.packetcoders.io/faster-pip-installs-with-uv/): `uv venv` followed by `source .venv/bin/activate`
Ensure that Python3.11+, openai, pptx and docx python libraries are installed. Run `uv pip install -r document2llm/requirements.txt`.
OCR of images belonging to the document is a WIP. That will require to install additional libraries: Run `uv pip install -r document2llm/requirements.ocr.txt`.

## Usage
To use Document2LLM, run the following command:
```bash
uv run document2llm -h
```
This will display the help message with available options.

### Options

The following options are available:

* `--from_document`: Specify the document to open
* `--to_document`: Specify the review document to create
* `--model_name`: Specify the name of the LLM model to use (default is `llama3.3-70b`)
* `--context_path`: Path to a text file where the context of the document is described (if not provided, headings will be used as context)
* `--detailed_analysis`: Select a detailed analysis or high-level one
* `--reviewer_properties`: Specify a reviewer properties (default is a SME able to first compose highly cost-effective teams and second is capable to set up very high-quality focused teams)
* `--debug`: Set logging to debug
* `--force_top_p`: Increases diversity from various probable outputs in results
* `--force_temperature`: Higher temperature increases non-sense and creativity while lower yields to focused and predictable results
* `--simulate_calls_only`: Do not perform the calls to LLM (used for debugging purposes)
* `--pre_post_requests`: Specify pre-post requests to format the output (default is `0`)
* `--context_length`: Specify the context length acceptable from the part of the source file (default is `120000`)
* `--enable_ocr`: When specified, will OCR any image found (this can require a lot of memory and is deactivated by default)

### PowerPoint Analysis

To analyze a PowerPoint presentation, run the following command:
```bash
python document2llm ppt -h
```
This will display the help message with available options for PowerPoint analysis.

The following options are available:

* `--skip_slides`: Specify slides to skip
* `--only_slides`: Specify slides to keep
* `--text_slide_requests`: Specify slide requests to process (default is `[0, 1, 2]`)
* `--no_text_slide_requests`: Skip text slide by slide check
* `--artistic_slide_requests`: Specify slide requests to process (default is `[0, 1, 2, 3]`)
* `--no_artistic_slide_requests`: Skip artistic slide by slide check
* `--deck_requests`: Specify deck requests to process (default is `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]`)
* `--no_deck_requests`: Skip deck check

Environment variables can point to a JSON file for additional requests:

* `DOC2LLM_REQUESTS_SLIDE_TEXT` for text requests per slide
* `DOC2LLM_REQUESTS_DECK_TEXT` for text requests for deck
* `DOC2LLM_REQUESTS_SLIDE_ARTISTIC` for graphical requests per slide

### Word Document Analysis

To analyze a Word document, run the following command:
```bash
python document2llm doc -h
```
This will display the help message with available options for Word document analysis.

The following options are available:

* `--skip_paragraphs`: Specify paragraphs to skip
* `--only_paragraphs`: Specify paragraphs to keep
* `--split_request_per_paragraph_deepness`: Specify paragraphs deepness to use to split requests
* `--paragraphs_requests`: Specify chapters requests to process (default is `[0, 1, 2, 3, 4, 5]`)

Environment variable `DOC2LLM_REQUESTS_DOC` can point to a JSON file for additional requests.

## LLM Requests
The script is able to perform various types of reviews that can easily be extended.

### LLM text Requests to be applied on each slide 
  * 0: Spell check and Clarity checks
  * 1: Slide Redability checks
  * 2: Slide take away checks
  * 3: Experts feedback checks
  * 4: Slide memorability check
  * 5: Slide audience check
  * 6: Slide weakness and counter points checks

### LLM artistic Requests to be applied on each slide 
  * 0: Artistic review
  * 1: Experts feedback checks
  * 2: Slide audience check
  * 3: Slide weakness and counter points checks

### LLM test Requests to be applied on the whole deck 
  * 0: Flow check
  * 1: Consistency check
  * 2: Clarity checks
  * 3: Deck Redability checks
  * 4: Deck take away checks
  * 5: Experts feedback checks
  * 6: Deck memorability check
  * 7: Deck audience check
  * 8: Deck weakness and counter points checks
  * 9: Summarize the deck

### LLM test Requests to be applied on word documents 
  * 0: Spell check and Clarity checks 
  * 1: Text Readability checks 
  * 2: Extract Commercial details 

## Script Extensibility

### Environment Variables
The following environment variables are required to run the program:
* `OPENAI_BASE_URL`: The URL adress of your LLM (For example: `https://api.openai.com/v1`) 
* `OPENAI_API_KEY`: Your OpenAI API key
* `DOC2LLM_REQUESTS_SLIDE_TEXT`: Path to the JSON file containing your additional requests for text in slide per slide 
* `DOC2LLM_REQUESTS_SLIDE_ARTISTIC`: Path to the JSON file containing your additional requests for artistic review in slide per slide 
* `DOC2LLM_REQUESTS_DECK_TEXT`: Path to the JSON file containing your additional requests for text in overall deck and flow
* `DOC2LLM_REQUESTS_DOC`: Path to the JSON file containing your additional requests for word document
* `DOC2LLM_REQUESTS_PRE_POST_REQUEST`: Path to the JSON file containing pre post requests to encapsulate your requests typically used when formatting is expected

### Creating your own request
The script is designed to be extensible, allowing users to create new custom requests that can be integrated into any of the above analysis. To achieve this, a JSON file must be created with the following schema:
```json
[
    {
        "request_name": "My request name",
        "request": "Detail your request here.",
        "temperature": 0.3, 
        "top_p": 0.7 
    }, 
    ...
]
```

This JSON file must be referenced using one of the following environment variables:
* `DOC2LLM_REQUESTS_SLIDE_TEXT`
* `DOC2LLM_REQUESTS_SLIDE_ARTISTIC`
* `DOC2LLM_REQUESTS_DECK_TEXT`
* `DOC2LLM_REQUESTS_DOC`

Example for Linux: `export DOC2LLM_REQUESTS_DOC=my_file.json`

### Creating parametrizable requests

Requests can contain environment variables in order to adapt requests or prompts to specific contexts. Say for example you need to extract technical or commercial details depending on specific contexts, in order to avoid duplicating prompts following is possible:

```json
[{"request_name": "Extract {DOC2LLM_DETAIL_TYPE, technical} details",
                "request": "* Extract all {DOC2LLM_DETAIL_TYPE, technical} details. * Provide {DOC2LLM_DETAIL_TYPE, technical} details as a list of bullet points. * Describe the complexity of the {DOC2LLM_DETAIL_TYPE, technical} expectation. * Prepare all necessary questions to ensure the {DOC2LLM_DETAIL_TYPE, technical} scope can be clarified.",
                "temperature": 0.3, "top_p": 0.2 
            }
]
```

Here the environment variable will be assigned the defaut value "technical" if it is not set. Default values are not mandatory: They are used if the environment varaiable is not set, if a variable is not set and no default value is provided, an empty string will replace the place holder.

In order to see the parametrization in action, do the following:
Example for Linux: 
* `export DOC2LLM_DETAIL_TYPE=commercial`
* `export DOC2LLM_REQUESTS_DOC=<your_json_file>.json`
* `python document2llm doc -h`

## Example Use Cases

* Review a PPT for high level clarity and readability:
```bash
python ppt2gpt.py --from_document mydoc.pptx --to_document mydoc.pptx .md  pptx --no_artistic_slide_requests --text_slide_requests 0,1,2 --deck_requests 0,1,2,3
```
* Review a PPT for expert and detailed feedback:
```bash
python ppt2gpt.py --from_document mydoc.pptx --to_document mydoc.pptx .md  --detailed pptx --no_artistic_slide_requests 
```
## LLM Model

The program uses the `llama3.3-70b` LLM model by default. You can specify a different model using the `--model_name` option.

## Improvements
* When a bunch of sentences are provided through bullet points, it is currently not possibke to notfy LLM that bullet points are in use.
* Enable variables in requests
* Enable OCR on images
* Enable GenAI Analysis of images
  
## Troubleshooting

If you encounter any issues, please check the logs for error messages.
Make sure to set the environment variables correctly.
If you're using a custom LLM model, ensure that it's properly configured and accessible. 