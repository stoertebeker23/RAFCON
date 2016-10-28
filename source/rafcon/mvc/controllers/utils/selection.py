import gtk
import glib
from gtk.gdk import CONTROL_MASK, SHIFT_MASK

from rafcon.mvc.controllers.utils.extended_controller import ExtendedController

from rafcon.utils import log
module_logger = log.get_logger(__name__)


class ListViewController(ExtendedController):
    """Class that implements a full selection control for lists that consists of a gtk.TreeView and a gtk.ListStore
    as model.

    :ivar gtk.ListStore list_store: List store that set by inherit class
    :ivar gtk.TreeView tree_view: Tree view that set by inherit class
    :ivar int ID_STORAGE_ID: Index for list store used to select entries set by inherit class
    :ivar int MODEL_STORAGE_ID: Index for list store used to update selections in state machine or tree view set by inherit class
    """
    ID_STORAGE_ID = None
    MODEL_STORAGE_ID = None
    _logger = None

    def __init__(self, model, view, tree_view, list_store, logger=None):
        super(ListViewController, self).__init__(model, view)
        self._logger = logger if logger is not None else module_logger
        self._do_selection_update = False
        self._last_path_selection = None
        self._setup_tree_view(tree_view, list_store)

    def register_view(self, view):
        """Register callbacks for button press events and selection changed"""
        self.tree_view.connect('button_press_event', self.mouse_click)
        self._tree_selection.connect('changed', self.selection_changed)
        self._tree_selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.update_selection_sm_prior()

    def _setup_tree_view(self, tree_view, list_store):
        self.tree_view = tree_view
        self.tree_view.set_model(list_store)
        self.list_store = list_store
        self._tree_selection = self.tree_view.get_selection()

    def _apply_value_on_edited_and_focus_out(self, renderer, apply_method):
        """Sets up the renderer to apply changed when loosing focus

        The default behaviour for the focus out event dismisses the changes in the renderer. Therefore we setup
        handlers for that event, applying the changes.

        :param gtk.CellRendererText renderer: The cell renderer who's changes are to be applied on focus out events
        :param apply_method: The callback method applying the newly entered value
        """
        assert isinstance(renderer, gtk.CellRenderer)

        def on_editing_canceled(renderer):
            """Disconnects the focus-out-event handler of cancelled editable

            :param gtk.CellRendererText renderer: The cell renderer who's editing was cancelled
            """
            editable = renderer.get_data("editable")
            editable.disconnect(editable.get_data("focus_out_handler_id"))
            renderer.disconnect(renderer.get_data("editing_cancelled_handler_id"))

        def on_focus_out(entry, event):
            """Applies the changes to the entry

            :param gtk.Entry entry: The entry that was focused out
            :param gtk.Event event: Event object with information about the event
            """
            editable = renderer.get_data("editable")
            editable.disconnect(editable.get_data("focus_out_handler_id"))
            renderer.disconnect(renderer.get_data("editing_cancelled_handler_id"))

            if self.get_path() is None:
                return
            # We have to use idle_add to prevent core dumps:
            # https://mail.gnome.org/archives/gtk-perl-list/2005-September/msg00143.html
            glib.idle_add(apply_method, self.get_path(), entry.get_text())

        def on_editing_started(renderer, editable, path):
            """Connects the a handler for the focus-out-event of the current editable

            :param gtk.CellRendererText renderer: The cell renderer who's editing was started
            :param gtk.CellEditable editable: interface for editing the current TreeView cell
            :param str path: the path identifying the edited cell
            """
            editing_cancelled_handler_id = renderer.connect('editing-canceled', on_editing_canceled)
            focus_out_handler_id = editable.connect('focus-out-event', on_focus_out)
            # Store reference to editable and signal handler ids for later access when removing the handlers
            renderer.set_data("editable", editable)
            renderer.set_data("editing_cancelled_handler_id", editing_cancelled_handler_id)
            editable.set_data("focus_out_handler_id", focus_out_handler_id)

        def on_edited(renderer, path, new_value_str):
            """Calls the apply method with the new value

            :param gtk.CellRendererText renderer: The cell renderer that was edited
            :param str path: The path string of the renderer
            :param str new_value_str: The new value as string
            """
            editable = renderer.get_data("editable")
            editable.disconnect(editable.get_data("focus_out_handler_id"))
            renderer.disconnect(renderer.get_data("editing_cancelled_handler_id"))
            apply_method(path, new_value_str)

        renderer.connect('editing-started', on_editing_started)
        renderer.connect('edited', on_edited)

    def on_right_click_menu(self):
        """An abstract method called after right click events"""
        raise NotImplementedError

    def get_view_selection(self):
        """Get actual tree selection object and all respective models of selected rows"""
        if not self.MODEL_STORAGE_ID:
            return None, None
        model, paths = self._tree_selection.get_selected_rows()
        selected_model_list = []
        for path in paths:
            model = self.list_store[path][self.MODEL_STORAGE_ID]
            selected_model_list.append(model)
        return self._tree_selection, selected_model_list

    def get_state_machine_selection(self):
        """An abstract getter method for state machine selection

        The method has to be implemented by inherit classes

        :return: selection
        :rtype: rafcon.mvc.selection.Selection
        """
        return None, None

    def get_selections(self):
        """Get actual model selection status in state machine selection and tree selection of the widget"""
        sm_selection, sm_selected_model_list = self.get_state_machine_selection()
        tree_selection, selected_model_list = self.get_view_selection()
        return tree_selection, selected_model_list, sm_selection, sm_selected_model_list

    def mouse_click(self, widget, event=None):
        """Implements shift- and control-key handling features for mouse button press events explicit

         The method is implements a fully defined mouse pattern to use shift- and control-key for multi-selection in a
         TreeView and a ListStore as model. It avoid problems caused by special renderer types like the text combo
         renderer by stopping the callback handler to continue with notifications.

        :param gtk.Object widget: Object which is the source of the event
        :param gtk.Object event: Event generated by mouse click
        :rtype: bool
        """
        # selection = self.tree_selection
        # print selection.get_mode(), bool(event.state & SHIFT_MASK), bool(event.state & CONTROL_MASK), type(event)

        if event.type == gtk.gdk.BUTTON_PRESS:
            pthinfo = self.tree_view.get_path_at_pos(int(event.x), int(event.y))

            if not bool(event.state & CONTROL_MASK) and not bool(event.state & SHIFT_MASK) and \
                    event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
                if pthinfo is not None:
                    model, paths = self._tree_selection.get_selected_rows()
                    # print paths
                    if pthinfo[0] not in paths:
                        # self._logger.info("force single selection for right click")
                        self.tree_view.set_cursor(pthinfo[0])
                        self._last_path_selection = pthinfo[0]
                    else:
                        # self._logger.info("single- or multi-selection for right click")
                        pass
                    self.on_right_click_menu()
                    return True

            if (bool(event.state & CONTROL_MASK) or bool(event.state & SHIFT_MASK)) and \
                    event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
                return True

            if not bool(event.state & SHIFT_MASK) and event.button == 1:
                if pthinfo is not None:
                    # self._logger.info("last select row {}".format(pthinfo[0]))
                    self._last_path_selection = pthinfo[0]
                # else:
                #     self._logger.info("deselect rows")
                #     self.tree_selection.unselect_all()

            if bool(event.state & SHIFT_MASK) and event.button == 1:
                # self._logger.info("SHIFT adjust selection range")
                model, paths = self._tree_selection.get_selected_rows()
                # print model, paths, pthinfo[0]
                if paths and pthinfo and pthinfo[0]:
                    if self._last_path_selection[0] <= pthinfo[0][0]:
                        new_row_ids_selected = range(self._last_path_selection[0], pthinfo[0][0]+1)
                    else:
                        new_row_ids_selected = range(self._last_path_selection[0], pthinfo[0][0]-1, -1)
                    # self._logger.info("range to select {0}, {1}".format(new_row_ids_selected, model))
                    self._tree_selection.unselect_all()
                    for path in new_row_ids_selected:
                        self._tree_selection.select_path(path)
                    return True
                else:
                    # self._logger.info("nothing selected {}".format(model))
                    if pthinfo and pthinfo[0]:
                        self._last_path_selection = pthinfo[0]

            if bool(event.state & CONTROL_MASK) and event.button == 1:
                # self._logger.info("CONTROL adjust selection range")
                model, paths = self._tree_selection.get_selected_rows()
                # print model, paths, pthinfo[0]
                if paths and pthinfo and pthinfo[0]:
                    if pthinfo[0] in paths:
                        self._tree_selection.unselect_path(pthinfo[0])
                    else:
                        self._tree_selection.select_path(pthinfo[0])
                    return True
                elif pthinfo and pthinfo[0]:
                    self._tree_selection.select_path(pthinfo[0])
                    return True

    def update_selection_sm_prior(self):
        """State machine prior update of tree selection"""
        if self._do_selection_update:
            return
        self._do_selection_update = True
        tree_selection, selected_model_list, sm_selection, sm_selected_model_list = self.get_selections()
        if tree_selection:
            for path, row in enumerate(self.list_store):
                model = row[self.MODEL_STORAGE_ID]
                if model not in sm_selected_model_list and model in selected_model_list:
                    tree_selection.unselect_path(path)
                if model in sm_selected_model_list and model not in selected_model_list:
                    tree_selection.select_path(path)

        self._do_selection_update = False

    def update_selection_self_prior(self):
        """Tree view prior update of state machine selection"""
        if self._do_selection_update:
            return
        self._do_selection_update = True
        tree_selection, selected_model_list, sm_selection, sm_selected_model_list = self.get_selections()
        if tree_selection:
            for row in self.list_store:
                model = row[self.MODEL_STORAGE_ID]
                if model in sm_selected_model_list and model not in selected_model_list:
                    sm_selection.remove(model)
                if model not in sm_selected_model_list and model in selected_model_list:
                    sm_selection.add(model)
        self._do_selection_update = False

    def selection_changed(self, widget, event=None):
        """Notify tree view about state machine selection"""
        # print type(self).__name__, "select changed", widget, event, self
        self.update_selection_self_prior()

    def select_entry(self, core_element_id, by_cursor=True):
        """Selects the row entry belonging to the given core_element_id by cursor or tree selection"""
        for row_num, element_row in enumerate(self.list_store):
            # Compare data port ids
            if element_row[self.ID_STORAGE_ID] == core_element_id:
                if by_cursor:
                    self.tree_view.set_cursor(row_num)
                else:
                    self.tree_view.get_selection().select_path((row_num, ))
                break

    def get_list_store_row_from_cursor_selection(self):
        """Returns the list_store_row of the currently by cursor selected row entry

        :return: List store row, None if there is no selection
        :rtype: gtk.TreeModelRow
        """
        path = self.get_path()
        if path is not None:
            return self.list_store[path]

    def get_path(self):
        """Get path to the currently selected entry row

        :return: path to the tree view cursor row, None if there is no selection
        :rtype: tuple
        """
        # the cursor is a tuple containing the current path and the focused column
        return self.tree_view.get_cursor()[0]


class TreeSelectionFeatureController(object):
    """Class that implements a full selection control for Trees that consists of a gtk.TreeView and a gtk.TreeStore
    as model.

    :ivar gtk.TreeStore tree_store: Tree store that set by inherit class
    :ivar gtk.TreeView tree_view: Tree view that set by inherit class
    :ivar int ID_STORAGE_ID: Index for list store used to select entries set by inherit class
    :ivar int MODEL_STORAGE_ID: Index for list store used to update selections in state machine or tree view set by inherit class
    """
    tree_store = None
    tree_view = None
    _logger = None
    ID_STORAGE_ID = None
    MODEL_STORAGE_ID = None

    def __init__(self, model, view, logger=None):
        assert isinstance(model, gtk.TreeStore)
        assert isinstance(view, gtk.TreeView)
        assert self.tree_store is model
        assert self.tree_view is view
        self._logger = logger if logger is not None else module_logger
        self._do_selection_update = False
        self._tree_selection = self.tree_view.get_selection()
        self._last_path_selection = None

    def register_view(self, view):
        """Register callbacks for button press events and selection changed"""
        # self.tree_view.connect('button_press_event', self.mouse_click)
        self._tree_selection.connect('changed', self.selection_changed)
        self._tree_selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.update_selection_sm_prior()

    def get_view_selection(self):
        """Get actual tree selection object and all respective models of selected rows"""
        model, paths = self._tree_selection.get_selected_rows()
        selected_model_list = []
        for path in paths:
            model = self.tree_store[path][self.MODEL_STORAGE_ID]
            selected_model_list.append(model)
        return self._tree_selection, selected_model_list

    def get_state_machine_selection(self):
        """An abstract getter method for state machine selection

        The method has to be implemented by inherit classes

        :return: selection
        :rtype: rafcon.mvc.selection.Selection
        """
        self._logger.info(self.__class__.__name__)
        raise NotImplementedError

    def get_selections(self):
        """Get actual model selection status in state machine selection and tree selection of the widget"""
        sm_selection, sm_selected_model_list = self.get_state_machine_selection()
        tree_selection, selected_model_list = self.get_view_selection()
        return tree_selection, selected_model_list, sm_selection, sm_selected_model_list

    def iter_tree_with_handed_function(self, function, *function_args):
        """Iterate tree view with condition check function"""
        def iter_all_children(state_row_iter, function, function_args):
            function(state_row_iter, *function_args)

            if isinstance(state_row_iter, gtk.TreeIter):
                for n in reversed(range(self.tree_store.iter_n_children(state_row_iter))):
                    child_iter = self.tree_store.iter_nth_child(state_row_iter, n)
                    iter_all_children(child_iter, function, function_args)
            else:
                self._logger.warning("Iter has to be TreeIter")

        iter_all_children(self.tree_store.get_iter_root(), function, function_args)

    def update_selection_sm_prior_condition(self, state_row_iter, selected_model_list, sm_selected_model_list):
        """State machine prior update of tree selection for one tree model row"""
        selected_path = self.tree_store.get_path(state_row_iter)
        tree_model_row = self.tree_store[selected_path]
        model = tree_model_row[self.MODEL_STORAGE_ID]
        # self._logger.info("check state {1} {2} {0}".format([model],
        #                                                    model in sm_selected_model_list,
        #                                                    model in selected_model_list))

        if model not in sm_selected_model_list and model in selected_model_list:
            # print type(self).__name__, "sm un-select model", model
            self._tree_selection.unselect_iter(state_row_iter)
        elif model in sm_selected_model_list and model not in selected_model_list:
            # print type(self).__name__, "sm select model", model
            self.tree_view.expand_to_path(selected_path)
            self._tree_selection.select_iter(state_row_iter)

    def update_selection_self_prior_condition(self, state_row_iter, sm_selection, selected_model_list, sm_selected_model_list):
        """Tree view prior update of one model in the state machine selection"""
        selected_path = self.tree_store.get_path(state_row_iter)
        tree_model_row = self.tree_store[selected_path]
        model = tree_model_row[self.MODEL_STORAGE_ID]
        # self._logger.info("check state {1} {2} {0}".format([model],
        #                                                    model in sm_selected_model_list,
        #                                                    model in selected_model_list))

        if model in sm_selected_model_list and model not in selected_model_list:
            # print type(self).__name__, "unselect model", model
            sm_selection.remove(model)
        elif model not in sm_selected_model_list and model in selected_model_list:
            # print type(self).__name__, "select model", model
            sm_selection.add(model)

    def update_selection_self_prior(self):
        """Tree view prior update of state machine selection"""
        if self._do_selection_update:
            return
        tree_selection, selected_model_list, sm_selection, sm_selected_model_list = self.get_selections()
        if sm_selection is None:
            return

        # self._logger.info("SELF SELECTION IS: {2}\nSELF {0}, \nSM   {1}".format(selected_model_list, sm_selected_model_list,
        #                                                                         tree_selection.get_mode()))
        self._do_selection_update = True
        self.iter_tree_with_handed_function(self.update_selection_self_prior_condition,
                                            sm_selection, selected_model_list, sm_selected_model_list)
        # tree_selection, selected_model_list, sm_selection, sm_selected_model_list = self.get_selections()
        # print selected_model_list, sm_selected_model_list

        self._do_selection_update = False

    def update_selection_sm_prior(self):
        """State machine prior update of tree selection"""
        if self._do_selection_update:
            return
        tree_selection, selected_model_list, sm_selection, sm_selected_model_list = self.get_selections()
        if sm_selection is None:
            return

        # self._logger.info("SM SELECTION IS: {2}\n{0}, \n{1}".format(selected_model_list, sm_selected_model_list,
        #                                                             tree_selection.get_mode()))
        self._do_selection_update = True
        self.iter_tree_with_handed_function(self.update_selection_sm_prior_condition,
                                            selected_model_list, sm_selected_model_list)
        # tree_selection, selected_model_list, sm_selection, sm_selected_model_list = self.get_selections()
        # print selected_model_list, sm_selected_model_list
        self._do_selection_update = False

    def selection_changed(self, widget, event=None):
        """Notify tree view about state machine selection"""
        # print type(self).__name__, "select changed", widget, event, self
        self.update_selection_self_prior()