#ifndef __TRACYDEBUG_HPP__
#define __TRACYDEBUG_HPP__

#include "TracyMangle.hpp"

#ifdef TRACY_ON_DEMAND
#  define TRACY_VERBOSE_EARLY_OUT_COND if( !GetProfiler().IsConnected() ) break
#else
// Skip rather than assert: TracyDebug can fire during Profiler member
// construction (e.g. SysPower ctor scanning intel-rapl), before s_instance is
// set, so ProfilerAvailable() is legitimately false.
#  define TRACY_VERBOSE_EARLY_OUT_COND if( !tracy::ProfilerAvailable() ) break
#endif

#define TracyInternalMessage( severity, ... )																				   \
	do {																													   \
        TRACY_VERBOSE_EARLY_OUT_COND;																						   \
		char buffer[4096];																									   \
		snprintf( buffer, sizeof(buffer), __VA_ARGS__ );																	   \
		tracy::Profiler::LogString( tracy::MessageSourceType::Tracy, severity, 0, TRACY_CALLSTACK, strlen( buffer ), buffer ); \
	} while( 0 )

#ifdef TRACY_VERBOSE
#  include <stdio.h>
#  ifdef _WIN32
#    include "../common/TracyWinFamily.hpp"
#  endif
#  if defined TRACY_WIN32_NO_DESKTOP
// There is no console to write to, so the debugger output window is the only sink available.
#    include <windows.h>
#    define TracyDebug(...) do {                                                                    \
        char tracyDebugBuf[4096];                                                                   \
        const int tracyDebugLen = snprintf( tracyDebugBuf, sizeof( tracyDebugBuf ) - 1, __VA_ARGS__ ); \
        const int tracyDebugEnd = tracyDebugLen < 0 ? 0 :                                           \
            ( tracyDebugLen < (int)sizeof( tracyDebugBuf ) - 1 ? tracyDebugLen : (int)sizeof( tracyDebugBuf ) - 2 ); \
        tracyDebugBuf[tracyDebugEnd] = '\n';                                                        \
        tracyDebugBuf[tracyDebugEnd+1] = '\0';                                                      \
        OutputDebugStringA( tracyDebugBuf );                                                        \
    } while( 0 )
#  else
#    define TracyDebug(...) do { fprintf( stderr, __VA_ARGS__ ); fputc( '\n', stderr ); } while( 0 )
#  endif
// Note: We can't use LogString when using TRACY_DELAYED_INIT due to a deadlock in the init code.
// This is caused by `GetProfilerData` triggering ProfileData ctor, which itself will call `GetProfilerData` and deadlock.
// TRACY_MANUAL_LIFETIME does not have this issue since StartupProfiler sets s_profilerData before calling the constructor.
// In general, this also means we can only call TracyDebug after and the first logging is after queue initialization and critical init (such as InitCallstackCritical).
#elif !defined(TRACY_NO_INTERNAL_MESSAGE) && (!defined(TRACY_DELAYED_INIT) || defined(TRACY_MANUAL_LIFETIME))
#  define TracyDebug(...) TracyInternalMessage( tracy::MessageSeverity::Debug, __VA_ARGS__ )
#else
#  define TracyDebug(...)
#endif

#endif
