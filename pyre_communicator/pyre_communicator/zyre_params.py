class ZyreParams(object):
    def __init__(self, node_name, groups, message_types):
        self.node_name = node_name
        self.groups = groups
        self.message_types = message_types

    def __str__(self):
        return str(self.node_name), str(self.groups), str(self.message_types)

