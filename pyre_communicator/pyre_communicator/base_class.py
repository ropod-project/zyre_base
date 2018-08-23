import pyre
import time
import uuid
import sys
import json
import zmq
from pyre import zhelper
import signal
import threading
import ast

from pyre.zactor import ZActor

class PyreBaseCommunicator(pyre.Pyre):
    def __init__(self, node_name, groups, message_types, verbose=False,
                 interface=None):
        super().__init__(name=node_name)

        self.group_names = groups
        self.message_types = message_types
        self.peer_adressbook = {}

        if interface:
            self.set_interface(interface)
            self.interface = interface

        self.verbose = verbose
        self.start()

        for group in groups:
            self.join(group)
            time.sleep(1)

        self.terminated = False

        self.ctx = zmq.Context()
        self.pipe = zhelper.zthread_fork(self.ctx, self.receive_loop)

    def receive_msg_cb(self, msg_content):
        pass

    def groups(self):
        return self.own_groups()

    def convert_zyre_msg_to_json(self):
        """Converts a zyre message to json"""
        pass

    def convert_zyre_msg_to_dict(self, msg):
        return ast.literal_eval(msg)

    def leave_groups(self, groups):
        for group in groups:
            self.leave(group)

    def generate_uuid(self):
        pass

    def get_time_stamp(self):
        pass

    def receive_loop(self, ctx, pipe):

        poller = zmq.Poller()
        poller.register(pipe, zmq.POLLIN)
        poller.register(self.socket(), zmq.POLLIN)

        while not self.terminated:
            try:
                items = dict(poller.poll())
                if pipe in items and items[pipe] == zmq.POLLIN:
                    message = pipe.recv()
                    if message.decode('utf-8') == "$$STOP":
                        break
                    print("CHAT_TASK: %s" % message)
                else:
                    self.received_msg = self.recv()
                    msg_type = self.received_msg.pop(0).decode('utf-8')
                    peer_uuid = self.received_msg.pop(0)
                    peer_name = self.received_msg.pop(0)


                    if self.verbose:
                        print("----- new message ----- ")
                        print("Type: ", msg_type)
                        print("Peer UUID: ", uuid.UUID(bytes=peer_uuid))
                        print("Peer Name: ", peer_name)

                    if msg_type == "SHOUT":
                        group_name = self.received_msg.pop(0)
                        print("Group: ", group_name)
                    elif msg_type == "ENTER":
                        headers = json.loads(self.received_msg.pop(0).decode('utf-8'))
                        print("Headers: ", headers)

                    msg_content = self.received_msg.pop(0)

                    if self.verbose:
                        print("Content: ", msg_content)

                    self.receive_msg_cb(msg_content)


            except (KeyboardInterrupt, SystemExit):
                self.terminated = True
                break
        self.ctx.term()
        print("Context status:", self.ctx.closed())
        self.stop()
        print("Exiting.......")

    def shout(self, msg, groups=None):
        """
        Shouts a message to a given group.
        For Python 3 encodes the string to utf-8

        Params:
            msg: the string to be sent
            groups: can be a string with the name of the group, or a list of
                    strings
        """

        if isinstance(msg, dict):
            message = str(dict).encode('utf-8')
        else:
            message = msg.encode('utf-8')

        if groups:
            if isinstance(groups, list):
                for group in groups:
                    super().shout(group, message)
                    time.sleep(1)
            else:
                # TODO Do we need formatted strings?
                super().shout(groups, message)
        else:
            for group in self.groups():
                super().shout(group, message)

    def whisper(self, msg, peer_uuid):
        """
        Whispers a message to a peer.
        For Python 3 encodes the message to utf-8.

        Params:
            msg: the string to be sent
            peer_uuid: string of 32 hexadecimal digits of the peer uuid
        """

        message = msg.encode('utf-8')

        if isinstance(peer_uuid, list):
            pass
        else:
            time.sleep(1)
            self.node.whispers(uuid.UUID(hex=peer_uuid), message)

    def test(self):
        print(self.name())
        print(self.own_groups())
        print(self.peers())

        time.sleep(1)
        for group in self.own_groups():
            self.shout("hello", group)
            time.sleep(1)
        # self.whisper("7315a4aa-1cf5-48f7-a609-b1d8417bb884", "hello whispering")


def main():
    test = PyreBaseCommunicator('test',
                                ["OTHER-GROUP", "CHAT", "TEST", "PYRE"],
                                ["TEST_MSG"],
                                True)
    test.test()


if __name__ == '__main__':
    main()
