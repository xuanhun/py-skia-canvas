#pragma once
#include <cassert>
#include <cstdlib>
#include "src/base/macros.h"
#define DCHECK(x) ((void)0)
#define CHECK(x) assert(x)
#define DCHECK_EQ(a,b) ((void)0)
#define DCHECK_NE(a,b) ((void)0)
#define DCHECK_LT(a,b) ((void)0)
#define DCHECK_LE(a,b) ((void)0)
#define DCHECK_GT(a,b) ((void)0)
#define DCHECK_GE(a,b) ((void)0)
#define DCHECK_IMPLIES(a,b) ((void)0)
#define UNREACHABLE() std::abort()
#define UNIMPLEMENTED() std::abort()
