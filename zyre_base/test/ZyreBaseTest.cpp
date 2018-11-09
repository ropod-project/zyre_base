#include "ZyreBase.h"
#include <iostream>
#include <sstream>

class ZyreBaseTest : public ZyreBase
{
    public:
    ZyreBaseTest(const std::string &nodeName,
	    const std::vector<std::string> &groups,
	    const std::vector<std::string> &messageTypes,
	    const bool &printAllReceivedMessages)
    : ZyreBase(nodeName, groups, messageTypes, printAllReceivedMessages)
    {};

    private:
    void recvMsgCallback(ZyreMsgContent* msgContent);
};

void ZyreBaseTest::recvMsgCallback(ZyreMsgContent* msgContent)
{
    //std::cout << this->getNodeName() << " received message" << "\n";
    //std::cout << message << "\n";
}

int main(int argc, char *argv[])
{
    std::vector<std::string> groups;
    groups.push_back("Group1");
    groups.push_back("Group2");
    groups.push_back("Group3");

    std::vector<std::string> messageTypes;
    bool b = true;

    {
        ZyreBaseTest test_node_1 = ZyreBaseTest("test_node_1", groups, messageTypes, b);
        ZyreBaseTest test_node_2 = ZyreBaseTest("test_node_2", groups, messageTypes, b);
        test_node_1.printJoinedGroups();
        test_node_2.printJoinedGroups();
        zclock_sleep(3000);
    }


    ZyreBaseTest test_node_1 = ZyreBaseTest("test_node_1", groups, messageTypes, b);
    ZyreBaseTest test_node_2 = ZyreBaseTest("test_node_2", groups, messageTypes, b);

    for (int i = 0; i < 10; i++)
    {
        std::stringstream msg;
        msg << "Hello to all groups NR " << i;
        test_node_1.shout(msg.str());
    }
    test_node_1.shout("Now only to group 3", "Group3");
    test_node_2.leaveGroup("Group2");
    test_node_1.shout("Now only to group 2", "Group2");
    test_node_2.printJoinedGroups();
    test_node_2.joinGroup("Group2");
    test_node_2.printJoinedGroups();
    test_node_1.shout("Now only to group 2 again", "Group2");

    zclock_sleep(15000);
    return 0;
}
