from abc import ABCMeta, abstractmethod
import components

class Website(metaclass=ABCMeta):
    def __init__(self):
        self.sections = []
        self.create_website()

    @abstractmethod
    def create_website():
        pass

    def get_sections(self):
        return self.sections

    def add_section(self, section):
        self.sections.append(section)