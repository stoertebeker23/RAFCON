import gtk
from gtk.gdk import CONTROL_MASK
from enum import Enum
from math import pow

from rafcon.mvc.singleton import state_machine_manager_model
from rafcon.mvc import statemachine_helper

from rafcon.mvc.config import global_gui_config

from gaphas.tool import Tool, ItemTool, HoverTool, HandleTool, RubberbandTool
from gaphas.item import NW
from gaphas.aspect import HandleFinder, ItemConnectionSink

from rafcon.mvc.mygaphas.aspect import HandleInMotion, Connector, StateHandleFinder
from rafcon.mvc.mygaphas.items.connection import ConnectionView, ConnectionPlaceholderView, TransitionView,\
    DataFlowView, FromScopedVariableDataFlowView, ToScopedVariableDataFlowView
from rafcon.mvc.mygaphas.items.ports import IncomeView, OutcomeView, InputPortView, OutputPortView, \
    ScopedVariablePortView
from rafcon.mvc.mygaphas.items.state import StateView, NameView
from rafcon.mvc.mygaphas.utils import gap_helper

from rafcon.utils import log
logger = log.get_logger(__name__)


MOVE_CURSOR = gtk.gdk.FLEUR

PortMoved = Enum('PORT', 'FROM TO')


class RemoveItemTool(Tool):
    """This tool is responsible of deleting the selected item
    """

    def __init__(self, graphical_editor_view, view=None):
        super(RemoveItemTool, self).__init__(view)
        self._graphical_editor_view = graphical_editor_view

    def on_key_release(self, event):
        if gtk.gdk.keyval_name(event.keyval) == "Delete":
            # Delete Transition from state machine
            if isinstance(self.view.focused_item, TransitionView):
                statemachine_helper.delete_model(self.view.focused_item.model)
                return True
            # Delete DataFlow from state machine
            if isinstance(self.view.focused_item, DataFlowView):
                statemachine_helper.delete_model(self.view.focused_item.model)
                return True
            # Delete selected state(s) from state machine
            if isinstance(self.view.focused_item, StateView):
                if self.view.has_focus():
                    self._graphical_editor_view.emit('remove_state_from_state_machine')
                    return True


class MoveItemTool(ItemTool):
    """This class is responsible of moving states, names, connections, etc.
    """

    def __init__(self, graphical_editor_view, view=None, buttons=(1,)):
        super(MoveItemTool, self).__init__(view, buttons)
        self._graphical_editor_view = graphical_editor_view

        self._item = None

    def on_button_press(self, event):
        super(MoveItemTool, self).on_button_press(event)

        item = self.get_item()
        if isinstance(item, StateView):
            self._item = item

        if (isinstance(self.view.focused_item, NameView) and not
                state_machine_manager_model.get_selected_state_machine_model().selection.is_selected(
                    self.view.focused_item.parent.model)):
            self.view.focused_item = self.view.focused_item.parent
            self._item = self.view.focused_item

        if not self.view.is_focus():
            self.view.grab_focus()
        if isinstance(self.view.focused_item, StateView):
            self._graphical_editor_view.emit('new_state_selection', self.view.focused_item)

        if event.button == 3:
            self._graphical_editor_view.emit('deselect_states')

        return True

    def on_button_release(self, event):

        for inmotion in self._movable_items:
            inmotion.move((event.x, event.y))
            rel_pos = gap_helper.calc_rel_pos_to_parent(self.view.canvas, inmotion.item,
                                                        inmotion.item.handles()[NW])
            if isinstance(inmotion.item, StateView):
                state_m = inmotion.item.model
                state_m.meta['gui']['editor_gaphas']['rel_pos'] = rel_pos
                state_m.meta['gui']['editor_opengl']['rel_pos'] = (rel_pos[0], -rel_pos[1])
            elif isinstance(inmotion.item, NameView):
                state_m = self.view.canvas.get_parent(inmotion.item).model
                state_m.meta['gui']['editor_gaphas']['name']['rel_pos'] = rel_pos

        if isinstance(self._item, StateView):
            self._item.moving = False
            self.view.canvas.request_update(self._item)
            self._graphical_editor_view.emit('meta_data_changed', self._item.model, "position", True)

            self._item = None

            self.view.redraw_complete_screen()

        if isinstance(self.view.focused_item, NameView):
            self._graphical_editor_view.emit('meta_data_changed', self.view.focused_item.parent.model,
                                             "name_position", False)

        return super(MoveItemTool, self).on_button_release(event)

    def on_motion_notify(self, event):
        """Normally do nothing.

        If a button is pressed move the items around.
        """
        if event.state & gtk.gdk.BUTTON_PRESS_MASK:

            if self._item and not self._item.moving:
                self._item.moving = True

            if not self._movable_items:
                # Start moving
                self._movable_items = set(self.movable_items())
                for inmotion in self._movable_items:
                    inmotion.start_move((event.x, event.y))

            for inmotion in self._movable_items:
                inmotion.move((event.x, event.y))

            return True


class HoverItemTool(HoverTool):

    def __init__(self, view=None):
        super(HoverItemTool, self).__init__(view)
        self._prev_hovered_item = None

    def on_motion_notify(self, event):
        super(HoverItemTool, self).on_motion_notify(event)
        from gaphas.tool import HandleFinder
        from gaphas.view import DEFAULT_CURSOR
        from gaphas.aspect import ElementHandleSelection

        view = self.view
        if view.hovered_handle:
            handle = view.hovered_handle
            view.hovered_handle = None
            port_v = self._prev_hovered_item.get_port_for_handle(handle)
            view.queue_draw_area(*port_v.get_port_area(view))
        pos = event.x, event.y

        # Reset cursor
        self.view.window.set_cursor(gtk.gdk.Cursor(DEFAULT_CURSOR))

        if isinstance(view.hovered_item, StateView):
            state_v, hovered_handle = HandleFinder(view.hovered_item, view).get_handle_at_point(pos)

            # Hover over port => show hover state of port and different cursor
            if hovered_handle and hovered_handle not in state_v.corner_handles:
                view.hovered_handle = hovered_handle
                port_v = state_v.get_port_for_handle(hovered_handle)
                view.queue_draw_area(*port_v.get_port_area(view))
                if event.state & gtk.gdk.CONTROL_MASK:
                    self.view.window.set_cursor(gtk.gdk.Cursor(MOVE_CURSOR))
                else:
                    self.view.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.CROSS))

            # Hover over corner/resize handles => show with cursor
            elif hovered_handle and hovered_handle in state_v.corner_handles:
                cursors = ElementHandleSelection.CURSORS
                index = state_v.handles().index(hovered_handle)
                self.view.window.set_cursor(cursors[index])

        # NameView should only be hovered, if its state is selected
        elif isinstance(view.hovered_item, NameView):
            state_v = self.view.canvas.get_parent(view.hovered_item)
            if state_v not in self.view.selected_items:
                view.hovered_item = state_v

        # Change mouse cursor to indicate option to move connection
        elif isinstance(view.hovered_item, ConnectionView):
            state_v = view.get_item_at_point_exclude(pos, selected=False, exclude=[view.hovered_item])
            if isinstance(state_v, StateView):
                distance = state_v.port_side_size / 2. * view.get_zoom_factor()
                connection_v, hovered_handle = StateHandleFinder(state_v, view).get_handle_at_point(pos, distance)
            else:
                connection_v, hovered_handle = HandleFinder(view.hovered_item, view).get_handle_at_point(pos)
            if hovered_handle:
                self.view.window.set_cursor(gtk.gdk.Cursor(MOVE_CURSOR))

        if self._prev_hovered_item and self.view.hovered_item is not self._prev_hovered_item:
            self._prev_hovered_item.hovered = False
        if isinstance(self.view.hovered_item, StateView):
            self.view.hovered_item.hovered = True
            self._prev_hovered_item = self.view.hovered_item


class MultiselectionTool(RubberbandTool):

    def __init__(self, graphical_editor_view, view=None):
        super(MultiselectionTool, self).__init__(view)

        self._graphical_editor_view = graphical_editor_view

    def on_button_press(self, event):
        if event.state & gtk.gdk.CONTROL_MASK and event.state & gtk.gdk.SHIFT_MASK:
            return super(MultiselectionTool, self).on_button_press(event)
        return False

    def on_motion_notify(self, event):
        if event.state & gtk.gdk.BUTTON_PRESS_MASK and event.state & gtk.gdk.CONTROL_MASK and \
                event.state & gtk.gdk.SHIFT_MASK:
            view = self.view
            self.queue_draw(view)
            self.x1, self.y1 = event.x, event.y
            self.queue_draw(view)
            return True

    def on_button_release(self, event):
        self.queue_draw(self.view)
        x0, y0, x1, y1 = self.x0, self.y0, self.x1, self.y1
        # Hold down ALT-key to add selection to current selection
        if event.state & gtk.gdk.MOD1_MASK:
            items_to_deselect = []
        else:
            items_to_deselect = list(self.view.selected_items)
        self.view.select_in_rectangle((min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)))

        for item in self.view.selected_items:
            if not isinstance(item, StateView):
                items_to_deselect.append(item)

        for item in items_to_deselect:
            if item in self.view.selected_items:
                self.view.unselect_item(item)

        self._graphical_editor_view.emit('new_state_selection', self.view.selected_items)

        return True


class HandleMoveTool(HandleTool):

    def __init__(self, graphical_editor_view, view=None):
        super(HandleMoveTool, self).__init__(view)

        self._graphical_editor_view = graphical_editor_view

        self._child_resize = False

        self._last_active_port = None
        self._new_connection = None

        self._start_state = None
        self._start_width = None
        self._start_height = None

        self._last_hovered_state = None

        self._active_connection_v = None
        self._active_connection_view_handle = None
        self._start_port = None  # Port where connection view pull starts
        self._check_port = None  # Port of connection view that is not pulled

        self._waypoint_list = None

    def on_button_press(self, event):
        view = self.view
        item, handle = HandleFinder(view.hovered_item, view).get_handle_at_point((event.x, event.y))

        if isinstance(item, ConnectionView):
            # If moved handles item is a connection save all necessary information (where did the handle start,
            # what is the connections other end)
            if handle is item.handles()[1] or handle is item.handles()[len(item.handles()) - 2]:
                return False
            self._active_connection_v = item
            self._active_connection_view_handle = handle
            if handle is item.from_handle():
                self._start_port = item.from_port
                self._check_port = item.to_port
            elif handle is item.to_handle():
                self._start_port = item.to_port
                self._check_port = item.from_port

        if isinstance(item, TransitionView):
            self._waypoint_list = item.model.meta['gui']['editor_gaphas']['waypoints']

        # Set start state
        if isinstance(item, StateView):
            self._start_state = item
            self._start_width = item.width
            self._start_height = item.height

        # Select handle
        return super(HandleMoveTool, self).on_button_press(event)

    def on_button_release(self, event):

        handle = self._active_connection_view_handle
        connection_v = self._active_connection_v
        handle_is_waypoint = connection_v and handle not in connection_v.end_handles()

        # Create new transition if pull beginning at port occurred
        if self._new_connection:
            # drop_item = self._get_drop_item((event.x, event.y))
            gap_helper.create_new_connection(self._new_connection.from_port,
                                             self._new_connection.to_port)

            # remove placeholder from canvas
            self._new_connection.remove_connection_from_ports()
            self.view.canvas.remove(self._new_connection)

        # if connection has been pulled to another port, update port
        elif self._last_active_port and self._last_active_port is not self._start_port and not handle_is_waypoint:
            if isinstance(connection_v, TransitionView):
                self._handle_transition_view_change(connection_v, handle)
            elif isinstance(connection_v, DataFlowView):
                self._handle_data_flow_view_change(connection_v, handle)
        # if connection has been put back to original position or is released on empty space, reset the connection
        elif (not self._last_active_port or
              self._last_active_port is self._start_port and connection_v) and not handle_is_waypoint:
            if isinstance(connection_v, TransitionView):
                self._reset_transition(connection_v, handle, self._start_port.parent)
            elif isinstance(connection_v, DataFlowView):
                self._reset_data_flow(connection_v, handle, self._start_port.parent)

        # Check, whether a transition waypoint was moved
        if isinstance(connection_v, TransitionView):
            gap_helper.update_meta_data_for_transition_waypoints(self._graphical_editor_view, connection_v,
                                                                 self._waypoint_list)

        if isinstance(self.grabbed_item, NameView):
            gap_helper.update_meta_data_for_name_view(self._graphical_editor_view, self.grabbed_item)

        elif isinstance(self.grabbed_item, StateView):
            only_ports = self.grabbed_handle not in self.grabbed_item.corner_handles
            if only_ports:
                gap_helper.update_meta_data_for_port(self._graphical_editor_view, self.grabbed_item,
                                                     self.grabbed_handle)
            else:
                gap_helper.update_meta_data_for_state_view(self._graphical_editor_view, self.grabbed_item,
                                                           self._child_resize)

        # reset temp variables
        self._last_active_port = None
        self._check_port = None
        self._new_connection = None
        self._start_state = None
        self._start_width = None
        self._start_height = None
        self._active_connection_v = None
        self._active_connection_view_handle = None
        self._waypoint_list = None
        self._last_hovered_state = None
        self._child_resize = False

        super(HandleMoveTool, self).on_button_release(event)

    def on_motion_notify(self, event):
        """Handle motion events

        If a handle is grabbed: drag it around, else, if the pointer is over a handle, make the owning item the
        hovered-item.
        """
        view = self.view
        # If no new transition exists and the grabbed handle is a port handle a new placeholder connection is
        # inserted into canvas
        # This is the default case if one starts to pull from a port handle
        if (not self._new_connection and self.grabbed_handle and event.state & gtk.gdk.BUTTON_PRESS_MASK and
                isinstance(self.grabbed_item, StateView) and not event.state & gtk.gdk.CONTROL_MASK):
            canvas = view.canvas
            # start_state = self.grabbed_item
            start_state = self._start_state
            start_state_parent = canvas.get_parent(start_state)

            handle = self.grabbed_handle
            start_port = gap_helper.get_port_for_handle(handle, start_state)

            # If the start state has a parent continue (ensure no transition is created from top level state)
            if (start_port and (isinstance(start_state_parent, StateView) or
                                (start_state_parent is None and isinstance(start_port, (IncomeView, InputPortView,
                                                                                        ScopedVariablePortView))))):

                # Go up one hierarchy_level to match the transitions line width
                transition_placeholder = isinstance(start_port, IncomeView) or isinstance(start_port, OutcomeView)
                placeholder_v = ConnectionPlaceholderView(max(start_state.hierarchy_level - 1, 1),
                                                          transition_placeholder)
                self._new_connection = placeholder_v

                canvas.add(placeholder_v, start_state_parent)

                # Check for start_port type and adjust hierarchy_level as well as connect the from handle to the
                # start port of the state
                if isinstance(start_port, IncomeView):
                    placeholder_v.hierarchy_level = start_state.hierarchy_level
                    start_state.connect_to_income(placeholder_v, placeholder_v.from_handle())
                elif isinstance(start_port, OutcomeView):
                    start_state.connect_to_outcome(start_port.outcome_id, placeholder_v, placeholder_v.from_handle())
                elif isinstance(start_port, InputPortView):
                    start_state.connect_to_input_port(start_port.port_id, placeholder_v, placeholder_v.from_handle())
                elif isinstance(start_port, OutputPortView):
                    start_state.connect_to_output_port(start_port.port_id, placeholder_v, placeholder_v.from_handle())
                elif isinstance(start_port, ScopedVariablePortView):
                    start_state.connect_to_scoped_variable_port(start_port.port_id, placeholder_v,
                                                                placeholder_v.from_handle())
                # Ungrab start port handle and grab new transition's to handle to move, also set motion handle
                # to just grabbed handle
                self.ungrab_handle()
                self.grab_handle(placeholder_v, placeholder_v.to_handle())
                self._set_motion_handle(event)

        # the grabbed handle is moved according to mouse movement
        if self.grabbed_handle and event.state & gtk.gdk.BUTTON_PRESS_MASK:
            item = self.grabbed_item
            handle = self.grabbed_handle
            pos = event.x, event.y

            if not self.motion_handle:
                self._set_motion_handle(event)

            snap_distance = self.view.pixel_to_cairo(global_gui_config.get_config_value("PORT_SNAP_DISTANCE", 5))

            # If current handle is from_handle of a connection view
            if isinstance(item, ConnectionView) and item.from_handle() is handle:
                self._get_port_side_size_for_hovered_state(pos)
                self.check_sink_item(self.motion_handle.move(pos, snap_distance), handle, item)
            # If current handle is to_handle of a connection view
            elif isinstance(item, ConnectionView) and item.to_handle() is handle:
                self._get_port_side_size_for_hovered_state(pos)
                self.check_sink_item(self.motion_handle.move(pos, snap_distance), handle, item)
            elif isinstance(item, TransitionView) and handle not in item.end_handles():
                self.motion_handle.move(pos, 0.)
            # If current handle is port or corner of a state view (for ports it only works if CONTROL key is pressed)
            elif isinstance(item, StateView) and handle in item.corner_handles:
                old_size = (item.width, item.height)
                self.motion_handle.move(pos, 0.)
                if event.state & CONTROL_MASK:
                    self._child_resize = True
                    item.resize_all_children(old_size)
            elif isinstance(item, StateView):
                # Move handles only with ctrl modifier clicked
                if event.state & gtk.gdk.CONTROL_MASK:
                    self.motion_handle.move(pos, 0.)
            # All other handles
            else:
                self.motion_handle.move(pos, 5.0)

            return True

    def _get_port_side_size_for_hovered_state(self, pos):
        item_below = self.view.get_item_at_point(pos, False)
        if isinstance(item_below, NameView):
            item_below = self.view.canvas.get_parent(item_below)
        if isinstance(item_below, StateView) and item_below is not self._last_hovered_state:
            self._last_hovered_state = item_below

    def _handle_data_flow_view_change(self, data_flow_v, handle):
        """Handle the change of a data flow origin or target modification

        The method changes the origin or target of an already existing data flow.

        :param data_flow_v: The data flow view that was changed
        :param handle: The handle of the changed port
        """
        start_parent = self._start_port.parent
        last_active_port_parent_state = self._last_active_port.parent.model.state
        modify_target = self._check_port == data_flow_v.from_port
        data_flow = data_flow_v.model.data_flow

        if modify_target:
            to_state_id = last_active_port_parent_state.state_id
            to_port_id = self._last_active_port.port_id

            try:
                data_flow.modify_target(to_state_id, to_port_id)
            except ValueError as e:
                logger.error(e)
                self._reset_data_flow(data_flow_v, handle, start_parent)
        else:
            from_state_id = last_active_port_parent_state.state_id
            from_port_id = self._last_active_port.port_id

            try:
                data_flow.modify_origin(from_state_id, from_port_id)
            except ValueError as e:
                logger.error(e)
                self._reset_data_flow(data_flow_v, handle, start_parent)

    def _handle_transition_view_change(self, transition_v, handle):
        """Handle the change of a transition origin or target modification

        The method changes the origin or target of an already existing transition.

        :param transition_v: The transition view that was changed
        :param handle: The handle of the changed port
        """
        start_parent = self._start_port.parent
        last_active_port_parent_state = self._last_active_port.parent.model.state
        modify_target = self._check_port == transition_v.from_port
        transition = transition_v.model.transition

        if modify_target:
            to_state_id = last_active_port_parent_state.state_id
            if isinstance(self._last_active_port, IncomeView):
                to_outcome_id = None
            else:
                to_outcome_id = self._last_active_port.outcome_id

            try:
                transition.modify_target(to_state_id, to_outcome_id)
            except ValueError as e:
                logger.error(e)
                self._reset_transition(transition_v, handle, start_parent)
        else:
            if isinstance(self._last_active_port, IncomeView):
                from_state_id = None
                from_outcome_id = None
            else:
                from_state_id = last_active_port_parent_state.state_id
                from_outcome_id = self._last_active_port.outcome_id

            try:
                transition.modify_origin(from_state_id, from_outcome_id)
            except ValueError as e:
                logger.error(e)
                self._reset_transition(transition_v, handle, start_parent)

    def _reset_transition(self, transition_v, handle, start_parent):
        """Reset a transition that has been modified

        :param transition_v: The view of the modified transition
        :param handle: The handle of the transition that has been modified
        :param start_parent: The parent state of the modified transition
        """
        if handle not in transition_v.handles():
            return

        self.disconnect_last_active_port(handle, transition_v)
        self.view.canvas.disconnect_item(transition_v, handle)

        if isinstance(self._start_port, OutcomeView):
            start_outcome_id = self._start_port.outcome_id
            start_parent.connect_to_outcome(start_outcome_id, transition_v, handle)
        else:
            start_parent.connect_to_income(transition_v, handle)

        self.view.canvas.update()

    def _reset_data_flow(self, data_flow_v, handle, start_parent):
        """Reset a data flow that has been modified

        :param data_flow_v: The view of the modified data flow
        :param handle: The handle of the data flow that has been modified
        :param start_parent: The parent state of the modified data flow
        """
        if handle not in data_flow_v.handles():
            return

        self.disconnect_last_active_port(handle, data_flow_v)
        self.view.canvas.disconnect_item(data_flow_v, handle)

        if isinstance(self._start_port, InputPortView):
            start_parent.connect_to_input_port(self._start_port.port_id, data_flow_v, handle)
        elif isinstance(self._start_port, OutputPortView):
            start_parent.connect_to_output_port(self._start_port.port_id, data_flow_v, handle)
        elif isinstance(self._start_port, ScopedVariablePortView):
            start_parent.connect_to_scoped_variable_port(self._start_port.port_id, data_flow_v, handle)

        self.view.canvas.update()

    def get_parents_parent_for_port(self, port):
        """Returns the StateView which is the parent of the StateView containing the port.

        If the ports parent is neither of Type StateView nor ScopedVariableView or the parent is the root state,
        None is returned.

        :param port: Port to return parent's parent
        :return: View containing the parent of the port, None if parent is root state or not of type StateView or
          ScopedVariableView
        """
        port_parent = port.parent
        if isinstance(port_parent, StateView):
            return self.view.canvas.get_parent(port_parent)
        else:
            return None

    def is_state_id_root_state(self, state_id):
        for state_v in self.view.canvas.get_root_items():
            if state_v.model.state.state_id == state_id:
                return True
        return False

    def _set_motion_handle(self, event):
        """Sets motion handle to currently grabbed handle
        """
        item = self.grabbed_item
        handle = self.grabbed_handle
        pos = event.x, event.y
        self.motion_handle = HandleInMotion(item, handle, self.view)
        self.motion_handle.start_move(pos)

    def check_sink_item(self, item, handle, connection):
        """Check for sink item

        Checks if the ConnectionSink's item is a StateView and if so tries for every port (income, outcome, input,
        output) to connect the ConnectionSink's port to the corresponding handle.
        If no matching_port was found or the item is no StateView the last active port is disconnected, as no valid
        connection is currently available for the connection.

        :param item: ItemConnectionSink holding the state and port to connect
        :param handle: Handle to connect port to
        :param connection: Connection containing handle
        """
        if isinstance(item, ItemConnectionSink):
            state = item.item
            if isinstance(state, StateView):
                if (isinstance(connection, TransitionView) or
                        (isinstance(connection, ConnectionPlaceholderView) and connection.transition_placeholder)):
                    if self.set_matching_port(state.get_logic_ports(), item.port, handle, connection):
                        return
                elif isinstance(connection, FromScopedVariableDataFlowView):
                    if handle is connection.from_handle():
                        if self.set_matching_port(state.scoped_variables, item.port, handle, connection):
                            return
                    elif handle is connection.to_handle():
                        if self.set_matching_port(state.inputs, item.port, handle, connection):
                            return
                elif isinstance(connection, ToScopedVariableDataFlowView):
                    if handle is connection.to_handle():
                        if self.set_matching_port(state.scoped_variables, item.port, handle, connection):
                            return
                    elif handle is connection.from_handle():
                        if self.set_matching_port(state.outputs, item.port, handle, connection):
                            return
                elif (isinstance(connection, DataFlowView) or
                        (isinstance(connection, ConnectionPlaceholderView) and not connection.transition_placeholder)):
                    if self.set_matching_port(state.get_data_ports(), item.port, handle, connection):
                        return
        self.disconnect_last_active_port(handle, connection)

    def disconnect_last_active_port(self, handle, connection):
        """Disconnects the last active port

        Updates the connected handles in the port as well as removes the port from the connected list in the connection.

        :param handle: Handle to disconnect from
        :param connection: ConnectionView to be disconnected, holding the handle
        """

        if self._last_active_port:
            self._last_active_port.remove_connected_handle(handle)
            self._last_active_port.tmp_disconnect()
            connection.reset_port_for_handle(handle)
            self._last_active_port = None

    def set_matching_port(self, port_list, matching_port, handle, connection):
        """Takes a list of PortViews and sets the port matching the matching_port to connected.

        It also updates the ConnectionView's connected port for the given handle and tells the PortView the new
        connected handle.
        If the matching port was found the last active port is disconnected and set to the matching_port

        :param port_list: List of ports to check
        :param matching_port: Port to look for in list
        :param handle: Handle to connect to matching_port
        :param connection: ConnectionView to be connected, holding the handle
        """
        port_for_handle = None

        for port in port_list:
            if port.port is matching_port:
                port_for_handle = port
                break

        if port_for_handle:
            if self._last_active_port is not port_for_handle:
                self.disconnect_last_active_port(handle, connection)
            port_for_handle.add_connected_handle(handle, connection, moving=True)
            port_for_handle.tmp_connect(handle, connection)
            connection.set_port_for_handle(port_for_handle, handle)
            self._last_active_port = port_for_handle
            # Redraw state of port to make hover state visible
            self.view.queue_draw_area(*port_for_handle.get_port_area(self.view))
            return True

        return False


class ConnectHandleMoveTool(HandleMoveTool):
    """Tool for connecting two items.

    There are two items involved. Handle of connecting item (usually
    a line) is being dragged by an user towards another item (item in
    short). Port of an item is found by the tool and connection is
    established by creating a constraint between line's handle and item's
    port.
    """

    def glue(self, item, handle, vpos):
        """Perform a small glue action to ensure the handle is at a proper location for connecting.
        """

        # glue_distance is the snapping radius
        if item.from_handle() is handle:
            glue_distance = 1.0 / pow(2, item.hierarchy_level)
        else:
            glue_distance = 1.0 / pow(2, item.hierarchy_level - 1)

        if self.motion_handle:
            return self.motion_handle.glue(vpos, glue_distance)
        else:
            return HandleInMotion(item, handle, self.view).glue(vpos, glue_distance)

    def connect(self, item, handle, vpos):
        """Connect a handle of a item to connectable item.

        Connectable item is found by `ConnectHandleTool.glue` method.

        :Parameters:
         item
            Connecting item.
         handle
            Handle of connecting item.
         vpos
            Position to connect to (or near at least)
        """
        connector = Connector(item, handle)

        # find connectable item and its port
        sink = self.glue(item, handle, vpos)

        # no new connectable item, then disconnect and exit
        if sink:
            connector.connect(sink)
        else:
            cinfo = item.canvas.get_connection(handle)
            if cinfo:
                connector.disconnect()

    def on_button_release(self, event):
        item = self.grabbed_item
        handle = self.grabbed_handle
        try:
            if handle and handle.connectable:
                self.connect(item, handle, (event.x, event.y))
        finally:
            return super(ConnectHandleMoveTool, self).on_button_release(event)