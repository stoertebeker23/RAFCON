from awesome_tool.mvc.controllers.extended_controller import ExtendedController
from awesome_tool.mvc.models.state_machine_manager import StateMachineManagerModel
from awesome_tool.mvc.views.network_connections import NetworkConnectionsView
from awesome_tool.utils import log

from awesome_tool.utils.network.network_connections import NetworkConnections

logger = log.get_logger(__name__)


class NetworkController(ExtendedController):

    def __init__(self, model, view):
        assert isinstance(model, StateMachineManagerModel)
        assert isinstance(view, NetworkConnectionsView)
        ExtendedController.__init__(self, model, view)

        base_path = model.get_selected_state_machine_model().state_machine.base_path
        self._network_connections = NetworkConnections(base_path, model)

        self._network_connections.connect('tcp_connected', self.tcp_connected)
        self._network_connections.connect('tcp_disconnected', self.tcp_disconnected)
        self._network_connections.connect('udp_response_received', self.udp_response_received)
        self._network_connections.connect('udp_no_response_received', self.udp_no_response_received)

    @property
    def network_connections(self):
        return self._network_connections

    def tcp_connected(self, nt_con):
        self.view["tcp_connection_connected_label"].set_text("YES")
        self.view["tcp_connect_button"].set_label("Disconnect TCP")

    def tcp_disconnected(self, nt_con):
        self.view["tcp_connection_connected_label"].set_text("NO")
        self.view["tcp_connect_button"].set_label("Connect TCP")

    def udp_response_received(self, nt_con):
        self.view["udp_connection_registered_label"].set_text("YES")

    def udp_no_response_received(self, nt_con):
        self.view["udp_connection_registered_label"].set_text("NO")

    def on_udp_register_button_clicked(self, widget, event=None):
        self.network_connections.register_udp()

    def on_tcp_connect_button_clicked(self, widget, event=None):
        self.network_connections.connect_tcp()