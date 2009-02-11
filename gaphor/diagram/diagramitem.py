"""
DiagramItem provides basic functionality for presentations.
Such as a modifier 'subject' property and a unique id.
"""

from zope import component
from gaphas.state import observed, reversible_property
from gaphor import UML
from gaphor.application import Application
from gaphor.core import inject
from gaphor.diagram import DiagramItemMeta
from gaphor.diagram.textelement import EditableTextSupport
from gaphor.diagram.style import ALIGN_CENTER, ALIGN_TOP


class StereotypeSupport(object):
    """
    Support for stereotypes for every diagram item.
    """
    STEREOTYPE_ALIGN = {
        'text-align'  : (ALIGN_CENTER, ALIGN_TOP),
        'text-padding': (5, 10, 2, 10),
        'text-outside': False,
        'text-align-group': 'stereotype',
    }

    def __init__(self):
        self._stereotype = self.add_text('stereotype',
                style=self.STEREOTYPE_ALIGN,
                visible=lambda: self._stereotype.text)
        self._show_stereotypes_attrs = False


    @observed
    def _set_show_stereotypes_attrs(self, value):
        self._show_stereotypes_attrs = value
        self.update_stereotypes_attrs()

    show_stereotypes_attrs = reversible_property(
            fget=lambda s: s._show_stereotypes_attrs,
            fset=_set_show_stereotypes_attrs,
            doc="""
            Diagram item should show stereotypes attributes when property
            is set to True.

            When changed, method `update_stereotypes_attrs` is called.
            """)

    def update_stereotypes_attrs(self):
        """
        Update display of stereotypes attributes.

        The method does nothing at the moment. In the future it should
        probably display stereotypes attributes under stereotypes header.

        Abstract class for classifiers overrides this method to display
        stereotypes attributes in compartments.
        """
        pass


    def set_stereotype(self, text=None):
        """
        Set the stereotype text for the diagram item.

        Note, that text is not Stereotype object.

        @arg text: stereotype text
        """
        self._stereotype.text = text
        self.request_update()

    stereotype = property(lambda s: s._stereotype, set_stereotype)

    def update_stereotype(self):
        """
        Update the stereotype definitions (text) of this item.

        Note, that this method is also called from
        ExtensionItem.confirm_connect_handle method.
        """
        # by default no stereotype, however check for __stereotype__
        # attribute to assign some static stereotype see interfaces,
        # use case relationships, package or class for examples
        stereotype = getattr(self, '__stereotype__', ())
        if stereotype:
            stereotype = self.parse_stereotype(stereotype)

        # Phew! :] :P
        stereotype = UML.model.stereotypes_str(self.subject, stereotype)
        self.set_stereotype(stereotype)


    def parse_stereotype(self, data):
        if isinstance(data, str): # return data as stereotype if it is a string
            return (data,)

        subject = self.subject

        for stereotype, condition in data.items():
            if isinstance(condition, tuple):
                cls, predicate = condition
            elif isinstance(condition, type):
                cls = condition
                predicate = None
            elif callable(condition):
                cls = None
                predicate = condition
            else:
                assert False, 'wrong conditional %s' % condition

            ok = True
            if cls:
                ok = type(subject) is cls #isinstance(subject, cls)
            if predicate:
                ok = predicate(self)

            if ok:
                return (stereotype,)
        return ()



class DiagramItem(UML.Presentation, StereotypeSupport, EditableTextSupport):
    """
    Basic functionality for all model elements (lines and elements!).

    This class contains common functionallity for model elements and
    relationships.
    It provides an interface similar to UML.Element for connecting and
    disconnecting signals.

    This class is not very useful on its own. It contains some glue-code for
    diacanvas.DiaCanvasItem and gaphor.UML.Element.

    Example:
        class ElementItem(diacanvas.CanvasElement, DiagramItem):
            connect = DiagramItem.connect
            disconnect = DiagramItem.disconnect
            ...

    @cvar style: styles information (derived from DiagramItemMeta)
    """

    __metaclass__ = DiagramItemMeta

    dispatcher = inject('property_based_dispatcher')

    def __init__(self, id=None):
        UML.Presentation.__init__(self)
        EditableTextSupport.__init__(self)
        StereotypeSupport.__init__(self)

        self._id = id

        # properties, which should be saved in file
        self._persistent_props = set()
        self._watched_properties = dict()

        self.add_watch(UML.Element.appliedStereotype, self.on_element_applied_stereotype)
        #self.add_watch(UML.Stereotype, self.on_element_applied_stereotype)

    id = property(lambda self: self._id, doc='Id')


    def set_prop_persistent(self, name):
        """
        Specify property of diagram item, which should be saved in file.
        """
        self._persistent_props.add(name)


    # UML.Element interface used by properties:

    # TODO: Use adapters for load/save functionality
    def save(self, save_func):
        if self.subject:
            save_func('subject', self.subject)

        save_func('show_stereotypes_attrs', self.show_stereotypes_attrs)

        # save persistent properties
        for p in self._persistent_props:
            save_func(p, getattr(self, p.replace('-', '_')))


    def load(self, name, value):
        if name == 'subject':
            type(self).subject.load(self, value)
        elif name == 'show_stereotypes_attrs':
            self._show_stereotypes_attrs = eval(value)
        else:
            #log.debug('Setting unknown property "%s" -> "%s"' % (name, value))
            try:
                setattr(self, name.replace('-', '_'), eval(value))
            except:
                log.warning('%s has no property named %s (value %s)' % (self, name, value))


    def postload(self):
        if self.subject:
            self.on_presentation_subject(None)
            self.update_stereotypes_attrs()


    def save_property(self, save_func, name):
        """
        Save a property, this is a shorthand method.
        """
        save_func(name, getattr(self, name.replace('-', '_')))


    def save_properties(self, save_func, *names):
        """
        Save a property, this is a shorthand method.
        """
        for name in names:
            self.save_property(save_func, name)


    def unlink(self):
        """
        Remove the item from the canvas and set subject to None.
        """
        if self.canvas:
            self.canvas.remove(self)
        super(DiagramItem, self).unlink()


    def request_update(self):
        """
        Placeholder for gaphor.Item's request_update() method.
        """
        pass

    def pre_update(self, context):
        EditableTextSupport.pre_update(self, context)

    def post_update(self, context):
        EditableTextSupport.post_update(self, context)

    def draw(self, context):
        EditableTextSupport.draw(self, context)


    def item_at(self, x, y):
        return self


    def on_element_applied_stereotype(self, event):
        if self.subject:
            self.update_stereotype()
            self.request_update()

    def on_subject_changed(self, event):
        if event and self.subject and self.subject is event.element:
            self.request_update()

    def add_watch(self, property, handler=None):
        """
        Add a property (umlproperty) to be watched. a handler may be provided
        that will be called with the event as argument (handler(event)).
        """
        assert isinstance(property, UML.properties.umlproperty)
        self._watched_properties[property] = handler or self.on_subject_changed


    def register_handlers(self):
        Application.register_handler(self.on_model_factory_event)
#        Application.register_handler(self.on_element_change)
        Application.register_handler(self.on_presentation_subject)
        dispatcher = self.dispatcher
        for class_, handler in self._watched_properties.iteritems():
            dispatcher.register_handler(class_, handler)

        # FixMe: calls to request_update() cause tests to fail
#        if self.subject:
#            self.on_presentation_subject(None)


    def unregister_handlers(self):
        Application.unregister_handler(self.on_model_factory_event)
        Application.unregister_handler(self.on_presentation_subject)
#        Application.unregister_handler(self.on_element_change)
        dispatcher = self.dispatcher
        for class_, handler in self._watched_properties.iteritems():
            dispatcher.unregister_handler(class_, handler)


    @component.adapter(UML.interfaces.IModelFactoryEvent)
    def on_model_factory_event(self, event):
        self.on_presentation_subject(None)


    @component.adapter(UML.interfaces.IAssociationSetEvent)
    def on_presentation_subject(self, event):
        if event is None or \
                (event.property is UML.Presentation.subject and \
                 event.element is self):
            for prop, handler in self._watched_properties.iteritems():
                if handler:
                    # Provide event?
                    handler(None)


    @component.adapter(UML.interfaces.IElementChangeEvent)
    def on_element_change(self, event):
        """
        Called when a model element has changed.
        """
        if event.property in self._watched_properties:
            handler = self._watched_properties[event.property]
            if handler:
                handler(event)
            elif self.subject and self.subject is event.element:
                self.request_update()


# vim:sw=4:et:ai
