"""
@author Jean-Philippe Ulpiano
"""
from domain.icontent_out import IContentOut
from typing import List, Dict
from pprint import pformat
import logging
import re
import pathlib  

class ContentOut(IContentOut):
    
    toc: List = []
    findings: Dict = {}
    TOTAL_FINDINGS: str = 'All findings'
    NAME_FINDING_KEY: str = 'name_finding'
    NUMBER_FINDING_KEY: str = 'number_finding'
    WEIGHT_FINDING_KEY: str = 'weight_finding'
    status: str = "Not initialized"
    
    def __init__(self, file_title: str, file_description: str, log_file_name: str, logger: logging.Logger, create_summary_findings: bool, max_nb_important_findings: int = 10):  
        self.log_file_name = log_file_name
        self.temporary_file_name = f"{log_file_name}.temporary"
        self.temporary_file = open(self.temporary_file_name, "a", encoding="utf-8") 
        self.file_content: List = []
        self.file_title = f'# {file_title}'
        self.file_description = file_description
        self.last_title_level = 1
        self.title_level_number: Dict = {}
        self.max_nb_important_findings = max_nb_important_findings
        self.create_summary_findings = create_summary_findings
        self.logger = logger
        self.add_title(1, "Introduction")
        self.document(file_description)

    def flush_and_close(self):
        with open(self.log_file_name, "w", encoding="utf-8") as file:
            
            file.write(f'{self.file_title}\n')
            if self.create_summary_findings:
                most_important_findings: str = self.__most_important_findings(self.max_nb_important_findings)
                if len(most_important_findings) > 0:
                    file.write(f'## Most important findings\n{most_important_findings}')
                else:
                    file.write(f'** Looks good: No most important findings could be found!!! **')

            file.write(f'## Table of content\n')
            for toc in self.toc:
                file.write(f'{toc}\n')
            for line in self.file_content:
                file.write(f'\n{line}\n')           

        self.temporary_file.close()
        pathlib.Path(self.temporary_file_name).unlink(missing_ok=True)

    def add_title(self, title_level: int, title_name: str):
        new_level:int = title_level + 1
        if new_level > self.last_title_level or new_level not in self.title_level_number:
            self.title_level_number[new_level] = 1
        else:
            self.title_level_number[new_level] += 1
        title_anchor: str = re.sub(r'\s', '-', title_name.lower()) 
        title: str = f'{"#" * (title_level + 1)} {title_name}'
        self.__append_log(title)
        self.toc.append(f'{"    " * max(title_level - 1, 0)}{self.title_level_number[new_level]}. [{title_name}](#{title_anchor})\n')

        self.last_title_level = new_level

    def __append_log(self, data: str):
        self.file_content.append(data)
        self.temporary_file.write(f"{data}\n")
        
    def document(self, line: str) -> str:
        md_text: str = '\n'.join([ re.sub(r'^#+', '#' * (self.last_title_level + 1), message) \
                                   for message in line.split('\\n')])
        self.__append_log(md_text)

        return md_text

    def document_response(self, slide_info: str, content: str) -> None:
        md_text: str = self.document(content)

        slide_findings: List = []
        if slide_info in list(self.findings.keys()):
            slide_findings = self.findings[slide_info]

        regexp: str = r'^\s*\|\s*(?P<' + self.NAME_FINDING_KEY + '>[^\|]*)\s*\|\s*(?P<' +\
                        self.NUMBER_FINDING_KEY + \
                            r'>\d+)\b[^\|]*\|\s*(?P<' + self.WEIGHT_FINDING_KEY + \
                                r'>\d+)\b[^\|]*\|\s*$'
        for reported_line in md_text.split('\n'):
            match = re.match(regexp, reported_line)
            if match:
                self.logger.debug(f"Found regexp match: {reported_line}")
                name_finding: str = str(match.group(self.NAME_FINDING_KEY)).strip()
                number_finding: int = int(match.group(self.NUMBER_FINDING_KEY))
                weight_finding: int = int(match.group(self.WEIGHT_FINDING_KEY))
                if name_finding == self.NAME_FINDING_KEY:
                    name_finding += '_'
                finding_updated: bool = False
                for finding in slide_findings:
                    if finding[self.NAME_FINDING_KEY] == name_finding and \
                       finding[self.WEIGHT_FINDING_KEY] == weight_finding:
                        finding[self.NUMBER_FINDING_KEY] += number_finding
                        self.logger.debug(f'Updated finding: {pformat(finding)}')
                        finding_updated = True
                        break

                if not finding_updated:
                    slide_findings.append(
                        {
                            self.NAME_FINDING_KEY: name_finding,
                            self.NUMBER_FINDING_KEY: number_finding,
                            self.WEIGHT_FINDING_KEY: weight_finding
                        })
                    self.logger.debug(f'Appended finding: {pformat(slide_findings[-1])}')
        total_penalties: int = 0
        slide_findings_with_total: List = []
        for finding in slide_findings:
            if finding[self.NAME_FINDING_KEY] != self.TOTAL_FINDINGS:
                slide_findings_with_total.append(finding)
                total_penalties += finding[self.NUMBER_FINDING_KEY] * finding[self.WEIGHT_FINDING_KEY]
        if len(slide_findings_with_total) > 0:
            slide_findings_with_total.append({
                self.NAME_FINDING_KEY: self.TOTAL_FINDINGS,
                self.NUMBER_FINDING_KEY: 1,
                self.WEIGHT_FINDING_KEY: total_penalties
            })
            self.logger.debug(f'Appended total finding ({len(slide_findings_with_total)} findings): {pformat(slide_findings_with_total[-1])}')

            self.findings[slide_info] = slide_findings_with_total
            self.logger.debug(f'Updated finding for {slide_info}:\n {len(self.findings)} total finding: {pformat(self.findings)}')

    def __most_important_findings(self, max_findings: int) -> str:
        slide_sorting_generation: List = []
        findings_str: str = 'findings'
        slide_info_str: str = 'slide_info'
        # Prepare data structure for sorting
        self.logger.debug(f'Iterating over Findings: {pformat(self.findings)}')
        for slide_info, findings in self.findings.items():
            self.logger.debug(f"Iterated: {slide_info}: \n{pformat(findings)}")
            total_penalties: int = 0
            for finding in findings:
                if finding[self.NAME_FINDING_KEY] == self.TOTAL_FINDINGS:
                    total_penalties = finding[self.WEIGHT_FINDING_KEY]
                    self.logger.debug(f'Total penalties for {slide_info} total finding: {total_penalties}')
                    break
            slide_sorting_generation.append({
                slide_info_str: slide_info, 
                findings_str: reversed(sorted(findings, key = lambda finding: finding[self.NUMBER_FINDING_KEY] * finding[self.WEIGHT_FINDING_KEY])), 
                self.TOTAL_FINDINGS: total_penalties
            })

            self.logger.debug(f'Appended to slide_sorting_generation: {pformat(slide_sorting_generation)}')
        self.logger.debug(f'slide_sorting_generation: {pformat(slide_sorting_generation)}')

        
        sorted_findings_str: str = ""
        sorted_findings: List = reversed(sorted(slide_sorting_generation, key = lambda findings: findings[self.TOTAL_FINDINGS]))
        self.logger.debug(f'sorted_findings: {pformat(sorted_findings)}')

        for index_sorted, sorted_finding in enumerate(sorted_findings):
            if index_sorted >= max_findings:
                break
            self.logger.debug(f'sorted_finding: Index: {index_sorted}: {pformat(sorted_finding)}, \nfindings_str: {pformat(findings_str)},\nslide_info_str: {slide_info_str} ')
            sorted_findings_str += f'### Slide {sorted_finding[slide_info_str]}\n'+\
                                   '| Finding type | Number findings | Weight | Total penalties |\n| --- | --- | --- | --- |\n'
            for finding in sorted_finding[findings_str]:
                self.logger.debug(f'finding: {pformat(finding)} ')

                sorted_findings_str += f'| {finding[self.NAME_FINDING_KEY]}'+\
                                       f' | {finding[self.NUMBER_FINDING_KEY]}'+\
                                       f' | {finding[self.WEIGHT_FINDING_KEY]}'+\
                                       f' | {finding[self.NUMBER_FINDING_KEY] * finding[self.WEIGHT_FINDING_KEY]} |\n'
        self.logger.debug(f'Generated findings: {sorted_findings_str}')
        return sorted_findings_str
                   



