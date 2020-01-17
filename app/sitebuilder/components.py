from abc import ABCMeta, abstractmethod

class Component(metaclass=ABCMeta):
    @abstractmethod
    def description(self):
        pass


class Bootstrap(Component):
    def __init__(self, styles=None, js=None, body=None):
        self.body = body
        self.styles = styles
        self.js = js


        def __repr__(self):
            return "Bootstrap | CSS"

        def get_resource(self, resource):
            resources = '<!-- Template Resources -->\n'
            if isinstance(resource, list):
                for item in self.resource:
                    resources += (item + '\n')
            else:
                resources += (item + '\n')

            return resources
