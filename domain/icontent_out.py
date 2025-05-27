from abc import ABC, abstractmethod
from typing import List

class IContentOut:
    @abstractmethod
    def flush_and_close(self):
        """
        """
    @abstractmethod
    def add_title(self, title_level: int, title_name: str) -> None:
        """
        """

    @abstractmethod
    def document(self, line: str) -> None:
        """
        """

    @abstractmethod
    def document_response(self, slide_info: str, content: str) -> None:
        """
        """
