import pyre
import time
import uuid
import json
import zmq
from pyre import zhelper
import ast
from datetime import timezone, timedelta, datetime

from pyre_base.zyre_params import ZyreMsg

ZYRE_SLEEP_TIME = 0.250  # type: float


class PyreBase(pyre.Pyre):
    def __init__(self, node_name, groups, message_types, verbose=False,
                 interface=None):
        super(PyreBase, self).__init__(name=node_name)

        self.group_names = groups

        assert isinstance(message_types, list)
        self.message_types = message_types
        self.peer_directory = {}

        if interface:
            self.set_interface(interface)
            self.interface = interface

        self.verbose = verbose
        self.start()

        assert isinstance(groups, list)
        for group in groups:
            self.join(group)
            time.sleep(ZYRE_SLEEP_TIME)
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
        except ValueError:
            return json.loads(msg)
        except Exception as e:
            print("Couldn't convert zyre_msg to dictionary")
            print(e)
            return None

    def leave_groups(self, groups):
        for group in groups:
            self.leave(group)

    def generate_uuid(self):
        """
        Returns a string containing a random uuid
        """
        return str(uuid.uuid4())

    def get_time_stamp(self, timedelta=None):
        """
        Returns a string containing the time stamp in ISO formato
        @param timedelta    datetime.timedelta object specifying the difference
                            between today and the desired date
        """
        if timedelta is None:
            return datetime.now(timezone.utc).isoformat()
        else:
            return (datetime.now(timezone.utc) + timedelta).isoformat()

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
                    if self.verbose:
                        print(self.received_msg)

                    zyre_msg = ZyreMsg(msg_type=self.received_msg.pop(0).decode('utf-8'),
                                       peer_uuid=uuid.UUID(bytes=self.received_msg.pop(0)),
                                       peer_name=self.received_msg.pop(0).decode('utf-8'))

                    if self.verbose:
                        print("----- new message ----- ")
                        print("Type: ", zyre_msg.msg_type)
                        print("Peer UUID: ", zyre_msg.peer_uuid)
                        print("Peer Name: ", zyre_msg.peer_name)

                    if zyre_msg.msg_type == "SHOUT":
                        zyre_msg.update(group_name=self.received_msg.pop(0))
                        if self.verbose:
                            print("Group: ", zyre_msg.group_name)
                    elif zyre_msg.msg_type == "ENTER":
                        zyre_msg.update(headers=json.loads(self.received_msg.pop(0).decode('utf-8')))

                        self.peer_directory[zyre_msg.peer_uuid] = zyre_msg.peer_name
                        if self.verbose:
                            print("Directory: ", self.peer_directory)
                            print("Headers: ", zyre_msg.headers)
                    elif zyre_msg.msg_type == "WHISPER":
                        pass
                    elif zyre_msg.msg_type == "JOIN":
                        pass
                    elif zyre_msg.msg_type == "LEAVE":
                        print(len(self.received_msg))
                        continue
                    elif zyre_msg.msg_type == "EXIT":
                        continue
                    elif zyre_msg.msg_type == "PING":
                        pass
                    elif zyre_msg.msg_type == "PING_OK":
                        pass
                    elif zyre_msg.msg_type == "HELLO":
                        pass
                    elif zyre_msg.msg_type == "STOP":
                        break
                    else:
                        print("Unrecognized message type!")

                    zyre_msg.update(msg_content=self.received_msg.pop(0).decode('utf-8'))

                    if self.verbose:
                        print("Content: ", zyre_msg.msg_content)

                    if zyre_msg.msg_type == "SHOUT" or zyre_msg.msg_type == "WHISPER":
                        self.receive_msg_cb(zyre_msg.msg_content)

            except (KeyboardInterrupt, SystemExit):
                self.terminated = True
                break
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

        if isinstance(msg, dict):
            # NOTE: json.dumps must be used instead of str, since it returns
            # the correct type of string
            message = json.dumps(msg).encode('utf-8')
        else:
            message = msg.encode('utf-8')

        if not peer and not peers and not peer_name and not peer_names:
            print("Need a peer to whisper to, doing nothing...")
            return

        if peer:
            super(PyreBase, self).whisper(peer, message)
        elif peers:
            for peer in peers:
                time.sleep(ZYRE_SLEEP_TIME)
                self.whispers(peer, message)
        elif peer_name:
            valid_uuids = [k for k, v in self.peer_directory.items() if v == peer_name]
            for peer_uuid in valid_uuids:
                time.sleep(ZYRE_SLEEP_TIME)
                super(PyreBase, self).whisper(peer_uuid, message)
        elif peer_names:
            for peer_name in peer_names:
                valid_uuids = [k for k, v in self.peer_directory.items() if v == peer_name]
                for peer_uuid in valid_uuids:
                    super(PyreBase, self).whisper(peer_uuid, message)
                time.sleep(ZYRE_SLEEP_TIME)

    def test(self):
        print(self.name())
        print(self.groups())
        print(self.peers())

        time.sleep(ZYRE_SLEEP_TIME)
        for group in self.own_groups():
            self.shout("hello", group)
            time.sleep(1)
        self.whisper("hello whispering", peer_name="chat_tester")
        self.whisper("hello whispering", peer_names=["chat_tester", "chat_tester"])

    def shutdown(self):
        self.stop()
        self.pipe.disable_monitor()
        self.pipe.close()
        self.ctx.term()
        self.terminated = True


def main():
    test = PyreBase('test',
                                ["OTHER-GROUP", "CHAT", "TEST", "PYRE"],
                                ["TEST_MSG"],
                                True)

    try:
        test.test()
        while True:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        test.shutdown()


if __name__ == '__main__':
    main()
