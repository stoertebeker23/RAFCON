import datetime


class NotificationOverview(dict):
    empty_info = {'before': True, 'model': None, 'method_name': None, 'instance': None,
                  'prop_name': None, 'args': (), 'kwargs': {}, 'info': {}}
    # TODO comment

    def __init__(self, info=None, with_prints=False):

        if info is None:
            info = self.empty_info
        self.info = info
        self.__type = 'before'
        if 'after' in info:
            self.__type = 'after'
        elif 'signal' in info:
            self.__type = 'after'
        self.with_prints = with_prints
        s, overview_dict = self.get_nice_info_dict_string(info)
        self.time_stamp = datetime.datetime.now()
        self._overview_dict = overview_dict
        dict.__init__(self, overview_dict)
        self.__description = s
        if self.with_prints:
            print str(self)

    def __str__(self):
        return self.__description

    def __setitem__(self, key, value):
        if key in ['info', 'model', 'prop_name', 'instance', 'method_name', 'level']:
            dict.__setitem__(self, key, value)

    @property
    def type(self):
        return self.__type

    def update(self, E=None, **F):
        if E is not None:
            for key in E.keys:
                if key not in ['info', 'model', 'prop_name', 'instance', 'method_name', 'level']:
                    E.pop(key)
            dict.update(self, E)

    def print_overview(self, overview=None):
        print self

    def get_nice_info_dict_string(self, info, level='\t', overview=None):
        """ Inserts all elements of a notification info-dictionary of gtkmvc or a Signal into one string and indicates
        levels of calls defined by 'kwargs'. Additionally, the elements get structured into a dict that holds all levels
        of the general notification key-value pairs in faster accessible lists. The dictionary has the element 'type'
        and the general elements {'model': [], 'prop_name': [], 'instance': [], 'method_name': [], 'args': [],
        'kwargs': []}) plus specific elements according the type. Type is always one of the following list
        ['before', 'after', 'signal'].
        """
        def get_nice_meta_signal_msg_tuple_string(meta_signal_msg_tuple, level, overview):
            meta_signal_dict = {}
            # origin
            s = "\n{0}origin={1}".format(level + "\t", meta_signal_msg_tuple.origin)
            meta_signal_dict['origin'] = meta_signal_msg_tuple.origin
            # change
            s += "\n{0}change={1}".format(level + "\t", meta_signal_msg_tuple.change)
            meta_signal_dict['change'] = meta_signal_msg_tuple.change
            # affects_children
            s += "\n{0}affects_children={1}".format(level + "\t", meta_signal_msg_tuple.affects_children)
            meta_signal_dict['affects_children'] = meta_signal_msg_tuple.affects_children
            overview['meta_signal'].append(meta_signal_dict)

            # notification (tuple)
            notification_dict = {}
            meta_signal_dict['notification'] = notification_dict
            if meta_signal_msg_tuple.notification is None:
                s += "\n{0}notification={1}".format(level + "\t", meta_signal_msg_tuple.notification)
            else:
                s += "\n{0}notification=Notification(".format(level + "\t")
                # model
                notification_dict['model'] = meta_signal_msg_tuple.notification.model
                s += "\n{0}model={1}".format(level + "\t\t", meta_signal_msg_tuple.notification.model)
                # prop_name
                notification_dict['prop_name'] = meta_signal_msg_tuple.notification.prop_name
                s += "\n{0}prop_name={1}".format(level + "\t\t", meta_signal_msg_tuple.notification.prop_name)
                # info
                notification_dict['info'] = meta_signal_msg_tuple.notification.info
                overview['kwargs'].append(meta_signal_msg_tuple.notification.info)
                s += "\n{0}info=\n{1}{0}\n".format(level + "\t\t",
                                               self.get_nice_info_dict_string(meta_signal_msg_tuple.notification.info,
                                                                              level+'\t\t\t',
                                                                              overview))
            return s

        overview_was_none = False
        if overview is None:
            overview_was_none = True
            overview = dict({'model': [], 'prop_name': [], 'instance': [], 'method_name': [], 'args': [], 'kwargs': []})
            overview['others'] = []
            overview['info'] = []
            if 'before' in info:
                overview['type'] = 'before'
            elif 'after' in info:
                overview['type'] = 'after'
                overview['result'] = []
            else:  # 'signal' in info:
                overview['type'] = 'signal'
                overview['meta_signal'] = []

        if ('after' in info or 'before' in info or 'signal' in info) and 'model' in info:
            if 'before' in info:
                s = "{0}'before': {1}".format(level, info['before'])
            elif 'after' in info:
                s = "{0}'after': {1}".format(level, info['after'])
            else:
                s = "{0}'signal': {1}".format(level, info['signal'])
        else:
            return str(info)
        overview['info'].append(info)
        # model
        s += "\n{0}'model': {1}".format(level, info['model'])
        overview['model'].append(info['model'])
        # prop_name
        s += "\n{0}'prop_name': {1}".format(level, info['prop_name'])
        overview['prop_name'].append(info['prop_name'])
        if not overview['type'] == 'signal':
            # instance
            s += "\n{0}'instance': {1}".format(level, info['instance'])
            overview['instance'].append(info['instance'])
            # method_name
            s += "\n{0}'method_name': {1}".format(level, info['method_name'])
            overview['method_name'].append(info['method_name'])
            # args
            s += "\n{0}'args': {1}".format(level, info['args'])
            overview['args'].append(info['args'])

            overview['kwargs'].append(info['kwargs'])
            if overview['type'] == 'after':
                overview['result'].append(info['result'])
            # kwargs
            s += "\n{0}'kwargs': {1}".format(level, self.get_nice_info_dict_string(info['kwargs'],
                                                                                   level + "\t",
                                                                                   overview))
            if overview['type'] == 'after':
                s += "\n{0}'result': {1}".format(level, info['result'])
            # additional elements not created by gtkmvc or common function calls
            overview['others'].append({})
            for key, value in info.items():
                if key in ['before', 'after', 'model', 'prop_name', 'instance', 'method_name', 'args', 'kwargs', 'result']:
                    pass
                else:
                    s += "\n{0}'{2}': {1}".format(level, info[key], key)
                    overview['others'][len(overview['others'])-1][key] = info[key]
        else:
            overview['kwargs'].append({})
            overview['meta_signal'].append(info['arg'])
            s += "\n{0}'arg': MetaSignalMsg({1}".format(level,
                                                        get_nice_meta_signal_msg_tuple_string(info['arg'],
                                                                                              level,
                                                                                              overview))

        if overview_was_none:
            return s, overview
        else:
            return s