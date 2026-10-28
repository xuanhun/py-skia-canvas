#pragma once
#include <cstdint>
#include <cstring>
#define V8_WARN_UNUSED_RESULT
#define V8_INLINE inline
namespace v8 { namespace base {
template<class To, class From> inline To bit_cast(const From& input) {
  static_assert(sizeof(To)==sizeof(From), "bit_cast widths must match");
  To result; std::memcpy(&result,&input,sizeof(result)); return result;
}
}}
