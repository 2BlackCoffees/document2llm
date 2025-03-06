
# PPT Review using LLM: An Extensible Python Program

This Python script utilizes a Large Language Model (LLM) to review and provide feedback on PowerPoint presentations (PPT). The program analyzes the content, structure, and overall quality of the presentation, offering a comprehensive review.


## Table of Contents

- [PPT Review using LLM: An Extensible Python Program](#ppt-review-using-llm-an-extensible-python-program)
  - [Table of Contents](#table-of-contents)
  - [Important Security Consideration](#important-security-consideration)
  - [Review Approaches](#review-approaches)
  - [Extensibility](#extensibility)
  - [Error Handling](#error-handling)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Usage](#usage)
  - [Options](#options)
  - [Default analysis](#default-analysis)
    - [LLM text Requests to be applied on each slide are:](#llm-text-requests-to-be-applied-on-each-slide-are)
    - [LLM artistic Requests to be applied on each slide are:](#llm-artistic-requests-to-be-applied-on-each-slide-are)
    - [LLM test Requests to be applied on the whole deck are:](#llm-test-requests-to-be-applied-on-the-whole-deck-are)
  - [LLM Model](#llm-model)
  - [Example Use Cases](#example-use-cases)
  - [Troubleshooting](#troubleshooting)

## Important Security Consideration
Please note that this script is highly configurable and should only be used with an LLM endpoint that ensures the privacy and security of your requests, especially when dealing with confidential information.

## Review Approaches
The program offers multiple review approaches, including:

* **Slide-by-Slide Text Review**: Analyzes the text content of each slide individually.
* **Artistic Colours and Disposition Review**: Evaluates the use of colors and layout, taking into account personal preferences and divergences.
* **Flow and Content Review**: Examines the overall flow and content of the entire presentation.
  
## Extensibility
The script is designed to be extensible, allowing users to create new custom requests that can be integrated into any of the above analysis. To achieve this, a JSON file must be created with the following schema:

```json
[
    {
        "request_name": "My request name",
        "request": "Detail your request here.",
        "temperature": 0.3, 
        "top_p": 0.7 
    }
]
```
This JSON file must be referenced using an environment variable. Please see the documentation for more information on this process.

## Error Handling
The program incorporates a backoff retry mechanism out of the box. However, if the number of tokens exceeds the limit, the script will stop executing. Currently, the only solution is to split the presentation into smaller parts. Note that token counting is not implemented, as this feature depends on the specific LLM being used.

## Prerequisites

Ensure that Python3 and openai libraries are installed.
Run `pip install -r magic-document-enhancer/requirements.txt`

## Environment Variables

The following environment variables are required to run the program:

* `OPENAI_BASE_URL`: The URL adress of your LLM (For example: `https://api.openai.com/v1`) 
* `OPENAI_API_KEY`: Your OpenAI API key
* `PPT2LLM_REQUESTS_SLIDE_TEXT`: Path to the JSON file containing your additional requests for text in slide per slide 
* `PPT2LLM_REQUESTS_SLIDE_ARTISTIC`: Path to the JSON file containing your additional requests for artistic review in slide per slide 
* `PPT2LLM_REQUESTS_DECK_TEXT`: Path to the JSON file containing your additional requests for text in overall deck and flow

## Usage

To run the program, use the following command:
```python ppt2gpt [options]``` 

## Options

The program accepts the following options:

*  `--from_document` FROM_DOCUMENT
                        Specify the document to open
*  `--model_name` MODEL_NAME
                        Specify the name of the LLM model to use. Default is llama3-70b
*  `--skip_slides` SKIP_SLIDES
                        Specify slides to skip: 1,2-5,8: Cannot be used with only_slides
*  `--only_slides` ONLY_SLIDES
                        Specify slides to keep: 1,2-5,8: Cannot be used with skip_slides
*  `--text_slide_requests` TEXT_SLIDE_REQUESTS
                        Specify slide requests to process: 1,3-5,7 from the following list: [[ 0: Spell check and Clarity checks *** 1: Slide Redability checks *** 2: Slide take away checks *** 3: Experts
                        feedback checks *** 4: Slide memorability check *** 5: Slide audience check *** 6: Slide weakness and counter points checks ]], default is [0, 1, 2, 3, 4, 5, 6]
*  `--no_text_slide_requests`
                        Skip text slide by slide check
*  `--artistic_slide_requests` ARTISTIC_SLIDE_REQUESTS
                        Specify slide requests to process: 1,3-5,7 from the following list: [[ 0: Artistic review *** 1: Experts feedback checks *** 2: Slide audience check *** 3: Slide weakness and counter
                        points checks ]], default is [0, 1, 2, 3]
*  `--no_artistic_slide_requests`
                        Skip artistic slide by slide check
*  `--deck_requests` DECK_REQUESTS
                        Specify deck requests to process: 1,3-5,7 from the following list: [[ 0: Flow check *** 1: Consistency check *** 2: Clarity checks *** 3: Deck Redability checks *** 4: Deck take away
                        checks *** 5: Experts feedback checks *** 6: Deck memorability check *** 7: Deck audience check *** 8: Deck weakness and counter points checks *** 9: Summarize the deck ]], default is
                        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
*  `--no_deck_requests`    Skip deck check
*  `--detailed_analysis`   Select a detailed analysis or high level one
*  `--reviewer_name` REVIEWER_NAME
                        Specify a reviewer name (Default is Elon Musk): Consider for example Jeff Bezos for management review.
*  `--debug`               Set logging to debug
*  `--force_top_p` FORCE_TOP_P
                        Increases diversity from various probable outputs in results.
*  `--force_temperature` FORCE_TEMPERATURE
                        Higher temperature increases non sense and creativity while lower yields to focused and predictable results.
*  `--simulate_calls_only`
                        Do not perform the calls to LLM: used for debugging purpose.


## Default analysis

### LLM text Requests to be applied on each slide are:
  * 0: Spell check and Clarity checks
  * 1: Slide Redability checks
  * 2: Slide take away checks
  * 3: Experts feedback checks
  * 4: Slide memorability check
  * 5: Slide audience check
  * 6: Slide weakness and counter points checks
### LLM artistic Requests to be applied on each slide are:
  * 0: Artistic review
  * 1: Experts feedback checks
  * 2: Slide audience check
  * 3: Slide weakness and counter points checks
### LLM test Requests to be applied on the whole deck are:
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

## LLM Model

The program uses the `llama3-70b` LLM model by default. You can specify a different model using the `--model_name` option.

## Example Use Cases

* Review a PPT for clarity and readability:
```bash
python ppt2gpt.py --text_slide_requests 0,1,2 --deck_requests 0,1,2,3 presentation.pptx
Review a PPT for artistic and expert feedback:
python ppt2gpt.py --artistic_slide_requests 0,1,2 --deck_requests 5,6,7,8,9 presentation.pptx
```

## Troubleshooting

If you encounter any issues, please check the logs for error messages.
Make sure to set the environment variables correctly.
If you're using a custom LLM model, ensure that it's properly configured and accessible