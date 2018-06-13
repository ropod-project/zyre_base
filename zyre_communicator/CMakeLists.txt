cmake_minimum_required(VERSION 3.9)
project(ccu_base)
set(CMAKE_CXX_STANDARD 17)

include_directories(include/)

set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/zyre_communicator/cmake")
find_package(zyre)
find_package(czmq)
find_package(libzmq)

set(TARGET test_base_communication)
set(SOURCE_FILES
    test/CCUtest.cpp
    src/ZyreBaseCommunicator.cpp
    )
set(LIBRARIES
        zyre
        czmq
        zmq)

add_executable(${TARGET} ${SOURCE_FILES})

target_link_libraries(${TARGET} ${LIBRARIES})

