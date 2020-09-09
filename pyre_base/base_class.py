import os
import pyre
import time
import uuid
import json
import zmq
from pyre import zhelper
import ast

from pyre_base.zyre_params import ZyreMsg

ZYRE_SLEEP_TIME = 0.250  # type: float


class PyreBase(pyre.Pyre):
    def __init__(self, node_name, groups, message_types, ctx=None, interface=None, **kwargs):
        super(PyreBase, self).__init__(name=node_name, ctx=ctx)
        self.group_names = groups

        assert isinstance(message_types, list)
        self.message_types = message_types
        self.peer_directory = {}

        if interface:
            self.set_interface(interface)
            self.interface = interface
        elif 'ZSYS_INTERFACE' in os.environ:
            interface = os.environ['ZSYS_INTERFACE']
            self.set_interface(interface)
            self.interface = interface

        self.terminated = False
        self.debug_msgs = kwargs.get('debug_msgs', True)

        self.pipe = zhelper.zthread_fork(self._ctx, self.receive_loop)

        assert isinstance(groups, list)
        for group in groups:
            time.sleep(ZYRE_SLEEP_TIME)
            self.join(group)

    def receive_msg_cb(self, msg_content):
        raise NotImplementedError

    def groups(self):
        return self.own_groups()

    def convert_zyre_msg_to_dict(self, msg):
        try:
            return ast.literal_eval(msg)
        except ValueError:
            return json.loads(msg)
        except Exception as e:
            print("Couldn't convert zyre_msg to dictionary")
            print(e)
            return None

    def leave_groups(self, groups):
        for group in groups:
            self.leave(group)

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

                    zyre_msg = self.get_zyre_msg()

                    if zyre_msg.msg_type in ('LEAVE', 'EXIT'):
                        continue
                    elif zyre_msg.msg_type == "STOP":
                        break
                    elif zyre_msg.msg_type not in ('WHISPER', 'JOIN', 'PING', 'PING_OK', 'HELLO', 'ENTER'):
                        self.logger.warning("Unrecognized message type: %s", zyre_msg.msg_type)

                    self.zyre_event_cb(zyre_msg)

            except (KeyboardInterrupt, SystemExit):
                self.terminated = True
                break
        print("Exiting.......")

    def get_zyre_msg(self):
        zyre_msg = ZyreMsg(msg_type=self.received_msg.pop(0).decode('utf-8'),
                           peer_uuid=uuid.UUID(bytes=self.received_msg.pop(0)),
                           peer_name=self.received_msg.pop(0).decode('utf-8'))

        # The following pyre message types don't need any further processing:
        # 'WHISPER', 'JOIN', 'PING', 'PING_OK', 'HELLO'
        if zyre_msg.msg_type in ('STOP', 'LEAVE'):
            return zyre_msg
        elif zyre_msg.msg_type == "SHOUT":
            zyre_msg.update(group_name=self.received_msg.pop(0).decode('utf-8'))
        elif zyre_msg.msg_type == "EXIT":
            if zyre_msg.peer_uuid in self.peer_directory:
                del self.peer_directory[zyre_msg.peer_uuid]
            self.logger.debug("Directory: %s", self.peer_directory)
            return zyre_msg
        elif zyre_msg.msg_type == "ENTER":
            zyre_msg.update(headers=json.loads(self.received_msg.pop(0).decode('utf-8')))

            self.peer_directory[zyre_msg.peer_uuid] = zyre_msg.peer_name
            self.logger.debug("Directory: %s", self.peer_directory)

        zyre_msg.update(msg_content=self.received_msg.pop(0).decode('utf-8'))

        if self.debug_msgs:
            self.logger.debug("----- new message ----- \n %s", zyre_msg)

        return zyre_msg

    def zyre_event_cb(self, zyre_msg):
        if zyre_msg.msg_type in ("SHOUT", "WHISPER"):
            self.receive_msg_cb(zyre_msg.msg_content)

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
            # NOTE: json.dumps must be used instead of str, since it returns
            # the correct type of string
            message = json.dumps(msg).encode('utf-8')
        else:
            message = msg.encode('utf-8')

        if groups:
            if isinstance(groups, list):
                for group in groups:
                    super(PyreBase, self).shout(group, message)
                    time.sleep(ZYRE_SLEEP_TIME)
            else:
                # TODO Do we need formatted strings?
                super(PyreBase, self).shout(groups, message)
        else:
            for group in self.groups():
                super(PyreBase, self).shout(group, message)

    def whisper(self, msg, peer=None):
        """
        Whispers a message to a peer.
        For Python 3 encodes the message to utf-8.

        Params:
            :string msg: the string to be sent
            :UUID peer: a single peer UUID
            :list peer: a list of peer UUIDs
            :string peer: the name of a peer
            :list peer: a list of peer names
        """

        if isinstance(msg, dict):
            # NOTE: json.dumps must be used instead of str, since it returns
            # the correct type of string
            message = json.dumps(msg).encode('utf-8')
        else:
            message = msg.encode('utf-8')

        if isinstance(peer, uuid.UUID):
            self.whisper_to_uuid(peer, message)
        elif isinstance(peer, list):
            for p in peer:
                time.sleep(ZYRE_SLEEP_TIME)
                if isinstance(p, uuid.UUID):
                    self.whisper_to_uuid(p, message)
                else:
                    self.whisper_to_name(p, message)
        elif isinstance(peer, str):
            self.whisper_to_name(peer, message)

    def whisper_to_uuid(self, peer, message):
        super(PyreBase, self).whisper(peer, message)

    def whisper_to_name(self, peer_name, message):
        for k, v in self.peer_directory.items():
            if v == peer_name:
                self.whisper_to_uuid(k, message)
                return

    def test(self):
        print(self.name())
        print(self.groups())
        print(self.peers())

        time.sleep(ZYRE_SLEEP_TIME)
        for group in self.own_groups():
            self.shout("hello", group)
            time.sleep(1)
        self.whisper("hello whispering", peer="chat_tester")
        self.whisper("hello whispering", peer=["chat_tester", "chat_tester"])

    def shutdown(self):
        self.stop()
        self.pipe.disable_monitor()
        self.pipe.close()
        self.terminated = True


def main():
    test = PyreBase('test',
                    ["OTHER-GROUP", "CHAT", "TEST", "PYRE"],
                    ["TEST_MSG"],
                    )

    try:
        test.start()
        test.test()
        while True:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        test.shutdown()


if __name__ == '__main__':
    main()
