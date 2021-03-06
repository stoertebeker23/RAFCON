# Copyright (C) 2015-2017 DLR
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Eclipse Public License v1.0 which
# accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
#
# Contributors:
# Franz Steinmetz <franz.steinmetz@dlr.de>
# Matthias Buettner <matthias.buettner@dlr.de>
# Rico Belder <rico.belder@dlr.de>
# Sebastian Brunner <sebastian.brunner@dlr.de>

from gtkmvc import View

from rafcon.gui import glade
from rafcon.gui.utils import constants


class StateOverviewView(View):
    builder = glade.get_glade_path("state_overview_widget.glade")
    top = 'properties_widget_bg'

    def __init__(self):
        View.__init__(self)

        self['properties_widget'].set_border_width(constants.GRID_SIZE * 2)
        # self['is_start_state_checkbutton'].set_border_width(constants.BUTTON_BORDER_WIDTH)
