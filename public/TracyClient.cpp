//
//          Tracy profiler
//         ----------------
//
// For fast integration, compile and
// link with this source file (and none
// other) in your executable (or in the
// main DLL / shared object on multi-DLL
// projects).
//

// Define TRACY_ENABLE to enable profiler.

#include "common/TracyWinFamily.hpp"
#include "common/TracySystem.cpp"

#ifdef TRACY_ENABLE

#ifdef _MSC_VER
#  pragma warning(push, 0)
#endif

#include "common/tracy_lz4.cpp"
#include "client/TracyProfiler.cpp"
#include "client/TracyCallstack.cpp"
#include "client/TracySysPower.cpp"
#include "client/TracySysTime.cpp"
#include "client/TracySysTrace.cpp"
#include "common/TracySocket.cpp"
#ifndef TRACY_HAS_CUSTOM_ALLOCATOR
#include "client/tracy_rpmalloc.cpp"
#endif
#include "client/TracyDxt1.cpp"
#include "client/TracyAlloc.cpp"
#include "client/TracyOverride.cpp"
#include "client/TracyKCore.cpp"

#ifdef TRACY_ROCPROF
#  include "client/TracyRocprof.cpp"
#endif
#ifdef _MSC_VER
#  ifdef TRACY_UWP
// Everything an app container may link against lives in this umbrella library.
#    pragma comment(lib, "WindowsApp.lib")
#  else
#    pragma comment(lib, "ws2_32.lib")
#    pragma comment(lib, "advapi32.lib")
#    pragma comment(lib, "user32.lib")
#  endif
#  pragma warning(pop)
#endif

#endif
