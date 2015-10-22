from gtkmvc import Observable
from yaml import YAMLObject
from weakref import ref


class StateElement(Observable, YAMLObject):
    """A base class for all elements of a state (ports, connections)

    It inherits from Observable to make a change of its fields observable. It also inherits from YAMLObject,
    in order to store/load it as YAML file.

    :ivar rafcon.statemachine.states.state.State parent: Parent state of the state element
    """

    _parent = None

    def __init__(self, parent=None):
        Observable.__init__(self)

        if type(self) == StateElement:
            raise NotImplementedError

        self.parent = parent

    @property
    def parent(self):
        """Getter for the parent state of the state element

        :return: None if parent is not defined, else the parent state
        :rtype: rafcon.statemachine.states.state.State
        """
        if not self._parent:
            return None
        return self._parent()

    @parent.setter
    @Observable.observed
    def parent(self, parent):
        """Setter for the parent state of the state element

        :param rafcon.statemachine.states.state.State parent: Parent state or None
        """
        if parent is None:
            self._parent = None
        else:
            from rafcon.statemachine.states.state import State
            assert isinstance(parent, State)

            old_parent = self.parent
            self._parent = ref(parent)

            valid, message = self._check_validity()
            if not valid:
                if not old_parent:
                    self._parent = None
                else:
                    self._parent = ref(old_parent)

                class_name = self.__class__.__name__
                raise ValueError("{0} invalid within state {1} (id {2}): {3}".format(class_name, parent.name,
                                                                                     parent.state_id, message))

    @classmethod
    def to_yaml(cls, dumper, data):
        raise NotImplementedError

    @classmethod
    def from_yaml(cls, loader, node):
        raise NotImplementedError

    def _change_property_with_validity_check(self, property_name, value):
        """Helper method to change a property and reset it if the validity check fails

        :param str property_name: The name of the property to be changed, e.g. '_data_flow_id'
        :param value: The new desired value for this property
        """
        assert isinstance(property_name, str)
        old_value = getattr(self, property_name)
        setattr(self, property_name, value)

        valid, message = self._check_validity()
        if not valid:
            setattr(self, property_name, old_value)
            class_name = self.__class__.__name__
            raise ValueError("The {2}'s '{0}' could not be changed: {1}".format(property_name[1:], message, class_name))

    def _check_validity(self):
        """Checks the validity of the state element's properties

        Some validity checks can only be performed by the parent. Thus, the existence of a parent and a check
        function must be ensured and this function be queried.

        :return: validity and messages
        :rtype: bool, str
        """
        if not self.parent:
            return True, "no parent"
        if not hasattr(self.parent, 'check_child_validity') or \
                not callable(getattr(self.parent, 'check_child_validity')):
            return True, "no parental check"
        return self.parent.check_child_validity(self)