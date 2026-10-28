#pragma once
#include <cstdarg>
#include <cstdio>
#include "src/base/vector.h"
namespace v8 { namespace base { inline int SNPrintF(Vector<char> s,const char* f,...){va_list a;va_start(a,f);int n=std::vsnprintf(s.begin(),s.length(),f,a);va_end(a);return n;} }}
namespace v8 { namespace base {
inline char HexCharOfValue(int value) {
  DCHECK(0 <= value && value <= 16);
  if (value < 10) return value + '0';
  return value - 10 + 'A';
}
}}
