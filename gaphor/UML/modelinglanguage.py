"""The UML Modeling Language module is the entrypoint for UML related
assets."""

from gaphor.abc import ModelingLanguage
from gaphor.core import gettext
from gaphor.diagram.diagramtoolbox import ToolboxDefinition
from gaphor.UML import diagramitems, uml
from gaphor.UML.toolbox import uml_toolbox_actions


class UMLModelingLanguage(ModelingLanguage):
    @property
    def name(self) -> str:
        return gettext("UML")

    @property
    def toolbox_definition(self) -> ToolboxDefinition:
        return uml_toolbox_actions

    def lookup_element(self, name):
        element_type = getattr(uml, name, None)
        if not element_type:
            element_type = getattr(diagramitems, name, None)
        return element_type
