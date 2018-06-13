#include "ZyreBaseCommunicator.h"
#include <iostream>
#include <cstdarg>
#include <algorithm>  // provides std::find
#include <sstream>

ZyreBaseCommunicator::ZyreBaseCommunicator(const std::string &nodeName,
		 const std::vector<std::string> &groups,
		 const std::vector<std::string> &messageTypes,
		 const bool &printAllReceivedMessages)
{
    this->params.nodeName = nodeName;
    this->params.messageTypes;
    this->printAllReceivedMessages = printAllReceivedMessages;
    this->params.groups = std::vector<std::string> {};  // will be filled by this->joinGroup()

    this->node = zyre_new(nodeName.c_str());
    if (!node)
        return;                 //  Could not create new node
    zyre_start(node);
    zclock_sleep(this->ZYRESLEEPTIME);

    joinGroup(groups);

    receiveActor = zactor_new(receiveLoop, this);
    assert(receiveActor);
}

ZyreBaseCommunicator::~ZyreBaseCommunicator()
{
    leaveGroup(params.groups);
    zactor_destroy(&receiveActor);
    zyre_stop(node);
    zclock_sleep(this->ZYRESLEEPTIME);
    zyre_destroy(&node);
}

void ZyreBaseCommunicator::printNodeName()
{
    std::cout << "nodeName: " << params.nodeName << std::endl;
}

void ZyreBaseCommunicator::printJoinedGroups()
{
    std::stringstream msg;
    msg << params.nodeName << "--- Printing joined groups: " << "\n";
    for (auto it = params.groups.begin(); it != params.groups.end(); it++)
    {
	    msg << "    " << *it << "\n";
    }
    msg << "\n";
    std::cout << msg.rdbuf();
}

void ZyreBaseCommunicator::printReceivingMessageTypes()
{
    std::cout << params.nodeName << "--- Printing receiving message Types: " << std::endl;
    for (auto it = params.messageTypes.begin(); it != params.messageTypes.end(); it++)
    {
	    std::cout << "    " << *it << std::endl;
    }
}

void ZyreBaseCommunicator::receiveLoop(zsock_t *pipe, void *args)
{
    ZyreBaseCommunicator* objectPtr = (ZyreBaseCommunicator*) args;

    zsock_signal (pipe, 0);     //  Signal "ready" to caller
    bool terminated = false;
    zpoller_t *poller = zpoller_new (pipe, zyre_socket (objectPtr->node), NULL);
    while (!terminated) {
        void *which = zpoller_wait (poller, -1);
        if (which == pipe) {
            zmsg_t* msg = zmsg_recv (which);
            if (!msg)
                break;              //  Interrupted

            char *command = zmsg_popstr (msg);
            if (streq (command, "$TERM"))
                terminated = true;
            // else
	    // if (streq (command, "SHOUT")) { 
            // char *string = zmsg_popstr (msg);
            // zyre_shouts (node, "CHAT", "%s", string);
	    // }
            else {
                puts ("E: invalid message to receiveActor");
                assert (false);
            }
            free (command);
            zmsg_destroy (&msg);
        }
        else
        if (which == zyre_socket (objectPtr->node)) {
            zmsg_t *msg = zmsg_recv (which);
            ZyreMsgContent* msgContent = objectPtr->zmsgToZyreMsgContent(msg);
            zmsg_destroy (&msg);

            if ((objectPtr->printAllReceivedMessages) and (msgContent->event != "EVASIVE"))
            {
                std::stringstream out_msg;
                out_msg << "---- " << objectPtr->params.nodeName << " Received Message -----" << std::endl;
                out_msg << "Event: " << msgContent->event << "\n";
                out_msg << "Peer: " <<  msgContent->peer << "\n";
                out_msg << "Name: " <<  msgContent->name << "\n";
                out_msg << "Group: " << msgContent->group << "\n";
                out_msg << "Message: " <<  msgContent->message << "\n\n";
                std::cout <<  out_msg.rdbuf();
            }
           objectPtr->recvMsgCallback(msgContent);
        }
    }
    zpoller_destroy (&poller);
}

zmsg_t* ZyreBaseCommunicator::stringToZmsg(std::string msg)
{
    zmsg_t* message = zmsg_new();
    zframe_t *frame = zframe_new(msg.c_str(), msg.size());
    zmsg_prepend(message, &frame);
    return message;
}

void ZyreBaseCommunicator::shout(const std::string &message, const std::vector<std::string> &groups)
{
    // TODO: check if subscribed to group
    // zstr_sendx(this->receiveActor, "SHOUT", message, groups, NULL);
    for (auto it = groups.begin(); it != groups.end(); it++)
    {
	    shout(message, *it);
    }
}

void ZyreBaseCommunicator::shout(const std::string &message)
{
    for (auto it = params.groups.begin(); it != params.groups.end(); it++)
    {
        shout(message, *it);
    }
}

void ZyreBaseCommunicator::shout(const std::string &message, const std::string &group)
{
    zyre_shouts(node, group.c_str(), "%s", message.c_str());
//    zmsg_t *msg = this->stringToZmsg(message);
//    zyre_shout(node, group.c_str(), &msg);
}


void ZyreBaseCommunicator::whisper(const std::string &message, const std::string &peer)
{
    zyre_whispers(node, peer.c_str(), "%s", message.c_str());
}

void ZyreBaseCommunicator::whisper(const std::string &message, const std::vector<std::string> &peers)
{
    for (auto it = peers.begin(); it != peers.end(); ++it)
    {
        whisper(message, *it);
    }
}

void ZyreBaseCommunicator::joinGroup(const std::string &group)
{
    auto it = std::find(params.groups.begin(), params.groups.end(), group);
    if (it == params.groups.end())  // if node is not subscribed to group
    {
	    zyre_join(node, group.c_str());
	    params.groups.push_back(group);
        zclock_sleep(this->ZYRESLEEPTIME);
    }
    else
    {
	    std::cout << "Trying to join: " << group << " but already joined... Doing nothing!" << std::endl;
    }
}

void ZyreBaseCommunicator::joinGroup(const std::vector<std::string> &groups)
{
    for (auto it = groups.begin(); it != groups.end(); it++)
    {
	    joinGroup(*it);
    }
}

void ZyreBaseCommunicator::leaveGroup(const std::string &group)
{
    leaveGroup(std::vector<std::string> {group});
}

void ZyreBaseCommunicator::leaveGroup(std::vector<std::string> groups)
{
    for (auto it = groups.begin(); it != groups.end(); it++)
    {
        auto paramsGroupPtr = std::find(params.groups.begin(), params.groups.end(), *it);
        if (paramsGroupPtr != params.groups.end())
        {
            zyre_leave(node, (*it).c_str());
            params.groups.erase(paramsGroupPtr);
        }
        else
        {
            // TODO: make this more sophisticated. Issue BlackBox?
            std::stringstream msg;
            msg << params.nodeName << " trying to leave group " << *it << " but node not in that group... Doing nothing!" << "\n";
            std::cout << msg.rdbuf();
        }
    }
}

ZyreMsgContent* ZyreBaseCommunicator::zmsgToZyreMsgContent(zmsg_t *msg)
{
    std::string sevent, speer, sname, sgroup, smessage;
    char *event, *peer, *name, *group, *message;
    event = zmsg_popstr(msg);
    peer = zmsg_popstr(msg);
    name = zmsg_popstr(msg);
    group = zmsg_popstr(msg);
    message = zmsg_popstr(msg);

    sevent = (event == nullptr) ? "" : event;
    speer = (peer == nullptr) ? "" : peer;
    sname = (name == nullptr) ? "" : name;
    sgroup = (group == nullptr) ? "" : group;
    smessage = (message == nullptr) ? "" : message;

    free(event);
    free(peer);
    free(name);
    free(group);
    free(message);

    ZyreMsgContent* msg_params = new ZyreMsgContent{sevent, speer, sname, sgroup, smessage};
    return msg_params;
}

void ZyreBaseCommunicator::printZyreMsgContent(const ZyreMsgContent &msgContent)
{

}