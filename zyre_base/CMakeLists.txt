cmake_minimum_required(VERSION 3.5)
project(zyre_base)

set (CMAKE_CXX_STANDARD 11)

find_package(PkgConfig)
pkg_check_modules(JSONCPP jsoncpp)
link_libraries(${JSONCPP_LIBRARIES})


include_directories(include/
    ${JSONCPP_INCLUDE_DIRS}
    )

set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/zyre_base/cmake")
find_package(zyre)
find_package(czmq)
find_package(libzmq)

pkg_check_modules(JSONCPP jsoncpp)
link_libraries(${JSONCPP_LIBRARIES})

set(TARGET test_base_communication)

set(SOURCE_FILES
    test/ZyreBaseTest.cpp
    src/ZyreBase.cpp
    )

set(LIBRARIES
        zyre
        czmq
        zmq)

add_executable(${TARGET} ${SOURCE_FILES})

target_link_libraries(${TARGET} ${LIBRARIES})
