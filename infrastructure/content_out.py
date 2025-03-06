from domain.icontent_out import IContentOut
from typing import List, Dict
import re
import pathlib  

class ContentOut(IContentOut):
    
    toc: List = []
    
    def __init__(self, file_title: str, file_description: str, log_file_name: str):  
        self.log_file_name = log_file_name
        self.temporary_file_name = f"{log_file_name}.temporary"
        self.temporary_file = open(self.temporary_file_name, "a", encoding="utf-8") 
        self.file_content: List = []
        self.file_title = f'# {file_title}'
        self.file_description = file_description
        self.last_title_level = 1
        self.title_level_number: Dict = {}
        self.add_title(1, "Introduction")
        self.document(file_description)

    def flush_and_close(self):
        with open(self.log_file_name, "w", encoding="utf-8") as file:
            
            file.write(f'{self.file_title}\n')
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
        


    def document(self, line: str) -> None:
        self.__append_log('\n'.join([ re.sub(r'^#+', '#' * (self.last_title_level + 1), message) for message in line.split('\\n')]))

