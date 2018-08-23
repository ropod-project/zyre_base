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
import datetime

from pyre.zactor import ZActor

class PyreBaseCommunicator(pyre.Pyre):
    def __init__(self, node_name, groups, message_types, verbose=False,
                 interface=None):
        super().__init__(name=node_name)

        self.group_names = groups
        self.message_types = message_types
        self.peer_directory = {}

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

    def convert_zyre_msg_to_dict(self, msg):
        try:
            return ast.literal_eval(msg)
        except:
            return None

    def leave_groups(self, groups):
        for group in groups:
            self.leave(group)

    def generate_uuid(self):
        """
        Returns a string containing a random uuid
        """
        return str(uuid.uuid4())

    def get_time_stamp(self):
        """
        Returns a string containing the time stamp in ISO format
        """
        return datetime.datetime.today().isoformat()

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
            message = str(msg).encode('utf-8')
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

    def whisper(self, msg, peer=None, peers=None, peer_name=None, peer_names=None):
        """
        Whispers a message to a peer.
        For Python 3 encodes the message to utf-8.

        Params:
            :string msg: the string to be sent
            :UUID peer: a single peer UUID
            :list peers: a list of peer UUIDs
            :string peer_name the name of a peer
            :list peer_names a list of peer names
        """

        message = msg.encode('utf-8')

        if not peer and not peers and not peer_name and not peer_names:
            print("Need a peer to whisper to, doing nothing...")
            return

        if peer:
            super().whisper(peer, message)
        elif peers:
            for peer in peers:
                time.sleep(1)
                self.whispers(peer, message)
        elif peer_name:
            time.sleep(1)
            valid_uuids = [k for k, v in self.peer_directory.items() if v == peer_name]
            for peer_uuid in valid_uuids:
                super().whisper(peer_uuid, message)
        elif peer_names:
            for peer_name in peer_names:
                valid_uuids = [k for k, v in self.peer_directory.items() if v == peer_name]
                for peer_uuid in valid_uuids:
                    super().whisper(peer_uuid, message)
                time.sleep(1)

    def test(self):
        print(self.name())
        print(self.groups())
        print(self.peers())

        time.sleep(1)
        for group in self.own_groups():
            self.shout("hello", group)
            time.sleep(1)
        self.whisper("hello whispering", peer_name="chat_tester")
        self.whisper("hello whispering", peer_names=["chat_tester", "chat_tester"])


def main():
    test = PyreBaseCommunicator('test',
                                ["OTHER-GROUP", "CHAT", "TEST", "PYRE"],
                                ["TEST_MSG"],
                                True)
    test.test()


if __name__ == '__main__':
    main()
